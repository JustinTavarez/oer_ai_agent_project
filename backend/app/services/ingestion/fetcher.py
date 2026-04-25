"""Idempotent raw fetcher for the real-data ingestion pipeline.

- Polite User-Agent (constant, no placeholder email).
- Per-host rate limit (1 req/sec) and basic retry/backoff.
- Conditional requests via ETag / Last-Modified: reruns are near-free when
  the server supports them.
- Writes <slug>.html plus a sibling <slug>.meta.json so parse-and-normalize
  can run without the network.

GGC Simple Syllabus is a JavaScript-rendered SPA: the public HTML body is a
near-empty shell unless rendered with a browser. To keep ingestion fast and
reliable, the GGC code path uses the public PDF export endpoint
(``/api2/doc-pdf/<id>/<tail>.pdf``) as the *primary* parseable artifact and
treats the HTML fetch as best-effort with a short, retry-free budget. A GGC
entry succeeds when the PDF lands; the HTML side is optional.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse

import httpx

from app.services.ingestion.manifest import ManifestEntry

logger = logging.getLogger(__name__)

USER_AGENT = "OER-AI-Agent/0.1 (+https://github.com/)"
REQUEST_TIMEOUT = 30.0
MAX_RETRIES = 2
RETRY_BACKOFF_SECONDS = 1.5
MIN_SECONDS_BETWEEN_HOST_REQUESTS = 1.0

# Short leash for GGC HTML — the SPA shell is useless and the server often
# stalls scripted requests. Don't let it slow the pipeline.
GGC_HTML_TIMEOUT = 8.0
GGC_HTML_THIN_BYTES = 2048

SOURCE_DIR_MAP = {
    "Open ALG": "openalg",
    "GGC Simple Syllabus": "ggc_syllabi",
}

GGC_DOC_RE = re.compile(
    r"^https?://ggc\.simplesyllabus\.com/(?:ui/locale-redirect\?/)?doc/([^/?#]+)/([^?#]+?)/?(?:\?.*)?$",
    re.IGNORECASE,
)


@dataclass
class FetchOutcome:
    entry: ManifestEntry
    status: str           # "fetched" | "not_modified" | "cached" | "error" | "skipped_todo"
    http_status: Optional[int] = None
    html_path: Optional[Path] = None
    meta_path: Optional[Path] = None
    pdf_path: Optional[Path] = None
    error: Optional[str] = None


def _slug_for(entry: ManifestEntry) -> str:
    url_hash = hashlib.sha1(entry.url.encode("utf-8")).hexdigest()[:12]
    tail = urlparse(entry.url).path.rstrip("/").rsplit("/", 1)[-1] or "page"
    safe_tail = re.sub(r"[^a-zA-Z0-9._-]+", "-", tail).strip("-").lower()[:60] or "page"
    return f"{url_hash}-{safe_tail}"


def _ggc_pdf_url(url: str) -> Optional[str]:
    """Derive the public PDF export URL from a /doc/<id>/<tail> syllabus URL.

    Examples:
      /doc/4cn8e7ppo/2025-Fall-ARTS-1100-Section-13-(81761)-?mode=view
        -> /api2/doc-pdf/4cn8e7ppo/2025-Fall-ARTS-1100-Section-13-(81761)-.pdf
      /ui/locale-redirect?/doc/<id>/<tail>?mode=view
        -> /api2/doc-pdf/<id>/<tail>.pdf
    """
    m = GGC_DOC_RE.match(url)
    if not m:
        return None
    doc_id = m.group(1)
    tail = m.group(2)
    if tail.lower().endswith(".pdf"):
        tail = tail[:-4]
    return f"https://ggc.simplesyllabus.com/api2/doc-pdf/{doc_id}/{tail}.pdf"


def _raw_dir(source: str, raw_root: Path) -> Path:
    sub = SOURCE_DIR_MAP.get(source)
    if not sub:
        raise ValueError(f"unknown source for raw dir: {source!r}")
    d = raw_root / sub
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load_meta(meta_path: Path) -> Dict:
    if not meta_path.exists():
        return {}
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _write_meta(meta_path: Path, meta: Dict) -> None:
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")


class _RateLimiter:
    def __init__(self, min_seconds: float) -> None:
        self.min_seconds = min_seconds
        self._last: Dict[str, float] = {}

    def wait(self, host: str) -> None:
        now = time.monotonic()
        last = self._last.get(host, 0.0)
        elapsed = now - last
        if last and elapsed < self.min_seconds:
            time.sleep(self.min_seconds - elapsed)
        self._last[host] = time.monotonic()


def _stamp_manifest_fields(meta: Dict, entry: ManifestEntry, slug: str) -> None:
    meta.update(
        {
            "course_code": entry.course_code,
            "source": entry.source,
            "title": entry.title,
            "term": entry.term,
            "resource_type": entry.resource_type,
            "notes": entry.notes,
            "mapping_rationale": entry.mapping_rationale,
            "subject_area": entry.subject_area,
            "slug": slug,
        }
    )


def _conditional_headers(prior: Dict, prefix: str = "") -> Dict[str, str]:
    headers: Dict[str, str] = {}
    etag = prior.get(f"{prefix}etag") if prefix else prior.get("etag")
    last_mod = (
        prior.get(f"{prefix}last_modified") if prefix else prior.get("last_modified")
    )
    if etag:
        headers["If-None-Match"] = etag
    if last_mod:
        headers["If-Modified-Since"] = last_mod
    return headers


def _fetch_with_retry(
    client: httpx.Client,
    url: str,
    headers: Dict[str, str],
    limiter: _RateLimiter,
    *,
    max_retries: int = MAX_RETRIES,
    backoff: float = RETRY_BACKOFF_SECONDS,
) -> Tuple[Optional[httpx.Response], Optional[str]]:
    """Returns (response, error). Response is None on terminal failure.

    Retries on transport errors and 5xx/429. Returns immediately on 2xx/3xx/4xx.
    """
    host = urlparse(url).netloc
    last_error: Optional[str] = None

    for attempt in range(max_retries + 1):
        limiter.wait(host)
        try:
            resp = client.get(url, headers=headers)
        except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            logger.warning("fetch attempt %d failed for %s: %s", attempt + 1, url, last_error)
            if attempt < max_retries:
                time.sleep(backoff * (attempt + 1))
            continue

        if resp.status_code >= 500 or resp.status_code == 429:
            last_error = f"HTTP {resp.status_code}"
            if attempt < max_retries:
                time.sleep(backoff * (attempt + 1))
                continue
        return resp, None

    return None, last_error or "unknown fetch error"


def _persist_html(
    body: str,
    resp: httpx.Response,
    html_path: Path,
    prior_meta: Dict,
    force: bool,
) -> Tuple[bool, str, Dict]:
    """Write HTML if changed; return (was_changed, sha256, html_meta_fragment)."""
    sha = hashlib.sha256(body.encode("utf-8", errors="ignore")).hexdigest()
    unchanged = (
        html_path.exists()
        and prior_meta.get("sha256") == sha
        and not force
    )
    if not unchanged:
        html_path.write_text(body, encoding="utf-8")
    fragment = {
        "url": str(resp.request.url),
        "final_url": str(resp.url),
        "http_status": resp.status_code,
        "content_type": resp.headers.get("content-type", ""),
        "content_length": len(body),
        "etag": resp.headers.get("etag"),
        "last_modified": resp.headers.get("last-modified"),
        "sha256": sha,
    }
    return (not unchanged), sha, fragment


def _persist_pdf(
    body: bytes,
    resp: httpx.Response,
    pdf_path: Path,
    prior_meta: Dict,
    force: bool,
) -> Tuple[bool, str, Dict]:
    sha = hashlib.sha256(body).hexdigest()
    unchanged = (
        pdf_path.exists()
        and prior_meta.get("pdf_sha256") == sha
        and not force
    )
    if not unchanged:
        pdf_path.write_bytes(body)
    fragment = {
        "pdf_url": str(resp.request.url),
        "pdf_final_url": str(resp.url),
        "pdf_http_status": resp.status_code,
        "pdf_content_type": resp.headers.get("content-type", ""),
        "pdf_content_length": len(body),
        "pdf_etag": resp.headers.get("etag"),
        "pdf_last_modified": resp.headers.get("last-modified"),
        "pdf_sha256": sha,
    }
    return (not unchanged), sha, fragment


def _fetch_ggc_entry(
    entry: ManifestEntry,
    raw_root: Path,
    client: httpx.Client,
    short_client: httpx.Client,
    limiter: _RateLimiter,
    force: bool,
) -> FetchOutcome:
    """GGC: PDF is primary, HTML is best-effort on a short leash."""
    dest_dir = _raw_dir(entry.source, raw_root)
    slug = _slug_for(entry)
    html_path = dest_dir / f"{slug}.html"
    pdf_path = dest_dir / f"{slug}.pdf"
    meta_path = dest_dir / f"{slug}.meta.json"

    prior_meta = _load_meta(meta_path)
    pdf_url = _ggc_pdf_url(entry.url)

    new_meta: Dict = dict(prior_meta) if prior_meta else {}
    _stamp_manifest_fields(new_meta, entry, slug)
    new_meta["last_checked"] = datetime.now(timezone.utc).isoformat()

    pdf_ok = False
    pdf_status: Optional[int] = None
    pdf_changed = False

    if pdf_url is None:
        new_meta["pdf_error"] = "could_not_derive_pdf_url"
        logger.error("could not derive PDF url for %s", entry.url)
    else:
        pdf_headers: Dict[str, str] = {"Accept": "application/pdf,*/*;q=0.8"}
        if pdf_path.exists() and not force:
            pdf_headers.update(_conditional_headers(prior_meta, prefix="pdf_"))

        resp, err = _fetch_with_retry(client, pdf_url, pdf_headers, limiter)
        if resp is None:
            new_meta["pdf_error"] = err or "unknown_pdf_error"
            logger.error("pdf fetch failed for %s: %s", pdf_url, err)
        elif resp.status_code == 304:
            new_meta["pdf_http_status"] = 304
            pdf_ok = True
            pdf_status = 304
        elif resp.status_code >= 400:
            new_meta["pdf_error"] = f"HTTP {resp.status_code}"
            new_meta["pdf_http_status"] = resp.status_code
            # The public GGC PDF endpoint usually returns 500; downgrade to info
            # so it doesn't drown out real errors. Normalize falls back to the
            # metadata-only path for these.
            logger.info("ggc pdf endpoint not available (HTTP %d) for %s", resp.status_code, pdf_url)
        else:
            body = resp.content
            if not body.startswith(b"%PDF-"):
                new_meta["pdf_error"] = "missing_pdf_magic_bytes"
                logger.error("pdf body did not start with %%PDF- for %s", pdf_url)
            else:
                pdf_changed, _, frag = _persist_pdf(body, resp, pdf_path, prior_meta, force)
                new_meta.update(frag)
                new_meta.pop("pdf_error", None)
                pdf_ok = True
                pdf_status = resp.status_code

    html_ok = False
    html_status: Optional[int] = None
    html_changed = False

    html_headers: Dict[str, str] = {}
    if html_path.exists() and not force:
        html_headers.update(_conditional_headers(prior_meta))

    try:
        host = urlparse(entry.url).netloc
        limiter.wait(host)
        resp = short_client.get(entry.url, headers=html_headers)
    except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPError) as exc:
        new_meta["html_error"] = f"short_leash_skip:{type(exc).__name__}"
        logger.warning(
            "GGC HTML short-leash skip for %s: %s", entry.url, type(exc).__name__
        )
    else:
        if resp.status_code == 304:
            new_meta["html_http_status"] = 304
            html_ok = True
            html_status = 304
        elif resp.status_code >= 400:
            new_meta["html_error"] = f"HTTP {resp.status_code}"
            new_meta["html_http_status"] = resp.status_code
        else:
            body = resp.text
            html_changed, _, frag = _persist_html(body, resp, html_path, prior_meta, force)
            new_meta.update(frag)
            new_meta.pop("html_error", None)
            html_ok = True
            html_status = resp.status_code
            if len(body) < GGC_HTML_THIN_BYTES:
                new_meta["html_thin"] = True
                logger.info(
                    "GGC HTML body looks like SPA shell (%d bytes) for %s — relying on PDF",
                    len(body), entry.url,
                )

    new_meta["fetched_at"] = datetime.now(timezone.utc).isoformat()

    if pdf_ok or html_ok:
        _write_meta(meta_path, new_meta)
        if pdf_changed or html_changed:
            status = "fetched"
        elif pdf_status == 304 or html_status == 304:
            status = "not_modified"
        else:
            status = "cached"
        return FetchOutcome(
            entry=entry,
            status=status,
            http_status=pdf_status or html_status,
            html_path=html_path if html_ok and html_path.exists() else None,
            pdf_path=pdf_path if pdf_ok and pdf_path.exists() else None,
            meta_path=meta_path,
        )

    return FetchOutcome(
        entry=entry,
        status="error",
        http_status=pdf_status or html_status,
        error=new_meta.get("pdf_error") or new_meta.get("html_error") or "ggc_fetch_failed",
    )


def _fetch_generic_entry(
    entry: ManifestEntry,
    raw_root: Path,
    client: httpx.Client,
    limiter: _RateLimiter,
    force: bool,
) -> FetchOutcome:
    """Generic HTML-only flow (used for Open ALG and any non-GGC source)."""
    dest_dir = _raw_dir(entry.source, raw_root)
    slug = _slug_for(entry)
    html_path = dest_dir / f"{slug}.html"
    meta_path = dest_dir / f"{slug}.meta.json"

    prior_meta = _load_meta(meta_path)
    headers: Dict[str, str] = {}
    if html_path.exists() and not force:
        headers.update(_conditional_headers(prior_meta))

    resp, err = _fetch_with_retry(client, entry.url, headers, limiter)
    if resp is None:
        return FetchOutcome(entry=entry, status="error", error=err)

    if resp.status_code == 304:
        new_meta = dict(prior_meta)
        new_meta["last_checked"] = datetime.now(timezone.utc).isoformat()
        new_meta["http_status"] = 304
        _stamp_manifest_fields(new_meta, entry, slug)
        _write_meta(meta_path, new_meta)
        return FetchOutcome(
            entry=entry,
            status="not_modified",
            http_status=304,
            html_path=html_path,
            meta_path=meta_path,
        )

    if resp.status_code >= 400:
        return FetchOutcome(
            entry=entry,
            status="error",
            http_status=resp.status_code,
            error=f"HTTP {resp.status_code}",
        )

    body = resp.text
    html_changed, _, frag = _persist_html(body, resp, html_path, prior_meta, force)
    meta = dict(frag)
    meta["fetched_at"] = datetime.now(timezone.utc).isoformat()
    meta["last_checked"] = meta["fetched_at"]
    _stamp_manifest_fields(meta, entry, slug)
    _write_meta(meta_path, meta)
    return FetchOutcome(
        entry=entry,
        status="fetched" if html_changed else "cached",
        http_status=resp.status_code,
        html_path=html_path,
        meta_path=meta_path,
    )


def fetch_entry(
    entry: ManifestEntry,
    raw_root: Path,
    client: httpx.Client,
    limiter: _RateLimiter,
    force: bool = False,
    short_client: Optional[httpx.Client] = None,
) -> FetchOutcome:
    if entry.is_todo():
        return FetchOutcome(entry=entry, status="skipped_todo")

    if entry.source == "GGC Simple Syllabus":
        sc = short_client or build_short_client()
        owns_short = short_client is None
        try:
            return _fetch_ggc_entry(entry, raw_root, client, sc, limiter, force)
        finally:
            if owns_short:
                sc.close()

    return _fetch_generic_entry(entry, raw_root, client, limiter, force)


def build_client() -> httpx.Client:
    return httpx.Client(
        timeout=REQUEST_TIMEOUT,
        follow_redirects=True,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        },
    )


def build_short_client() -> httpx.Client:
    """Short-timeout, no-retry client used only for GGC HTML (best-effort)."""
    return httpx.Client(
        timeout=httpx.Timeout(GGC_HTML_TIMEOUT, connect=GGC_HTML_TIMEOUT),
        follow_redirects=True,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        },
    )


def build_limiter() -> _RateLimiter:
    return _RateLimiter(MIN_SECONDS_BETWEEN_HOST_REQUESTS)
