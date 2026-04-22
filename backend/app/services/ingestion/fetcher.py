"""Idempotent raw fetcher for the real-data ingestion pipeline.

- Polite User-Agent (constant, no placeholder email).
- Per-host rate limit (1 req/sec) and basic retry/backoff.
- Conditional requests via ETag / Last-Modified: reruns are near-free when
  the server supports them.
- Writes <slug>.html plus a sibling <slug>.meta.json so parse-and-normalize
  can run without the network.
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
from typing import Dict, Optional
from urllib.parse import urlparse

import httpx

from app.services.ingestion.manifest import ManifestEntry

logger = logging.getLogger(__name__)

USER_AGENT = "OER-AI-Agent/0.1 (+https://github.com/)"
REQUEST_TIMEOUT = 30.0
MAX_RETRIES = 2
RETRY_BACKOFF_SECONDS = 1.5
MIN_SECONDS_BETWEEN_HOST_REQUESTS = 1.0

SOURCE_DIR_MAP = {
    "Open ALG": "openalg",
    "GGC Simple Syllabus": "ggc_syllabi",
}


@dataclass
class FetchOutcome:
    entry: ManifestEntry
    status: str           # "fetched" | "not_modified" | "cached" | "error" | "skipped_todo"
    http_status: Optional[int] = None
    html_path: Optional[Path] = None
    meta_path: Optional[Path] = None
    error: Optional[str] = None


def _slug_for(entry: ManifestEntry) -> str:
    url_hash = hashlib.sha1(entry.url.encode("utf-8")).hexdigest()[:12]
    tail = urlparse(entry.url).path.rstrip("/").rsplit("/", 1)[-1] or "page"
    safe_tail = re.sub(r"[^a-zA-Z0-9._-]+", "-", tail).strip("-").lower()[:60] or "page"
    return f"{url_hash}-{safe_tail}"


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


def fetch_entry(
    entry: ManifestEntry,
    raw_root: Path,
    client: httpx.Client,
    limiter: _RateLimiter,
    force: bool = False,
) -> FetchOutcome:
    if entry.is_todo():
        return FetchOutcome(entry=entry, status="skipped_todo")

    dest_dir = _raw_dir(entry.source, raw_root)
    slug = _slug_for(entry)
    html_path = dest_dir / f"{slug}.html"
    meta_path = dest_dir / f"{slug}.meta.json"

    prior_meta = _load_meta(meta_path)
    headers: Dict[str, str] = {}

    if html_path.exists() and not force:
        if prior_meta.get("etag"):
            headers["If-None-Match"] = prior_meta["etag"]
        if prior_meta.get("last_modified"):
            headers["If-Modified-Since"] = prior_meta["last_modified"]

    host = urlparse(entry.url).netloc
    last_error: Optional[str] = None

    for attempt in range(MAX_RETRIES + 1):
        limiter.wait(host)
        try:
            resp = client.get(entry.url, headers=headers)
        except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            logger.warning("fetch attempt %d failed for %s: %s", attempt + 1, entry.url, last_error)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
            continue

        if resp.status_code == 304:
            logger.info("not modified: %s", entry.url)
            new_meta = dict(prior_meta)
            new_meta["last_checked"] = datetime.now(timezone.utc).isoformat()
            new_meta["http_status"] = 304
            _write_meta(meta_path, new_meta)
            return FetchOutcome(
                entry=entry,
                status="not_modified",
                http_status=304,
                html_path=html_path,
                meta_path=meta_path,
            )

        if resp.status_code >= 500 or resp.status_code == 429:
            last_error = f"HTTP {resp.status_code}"
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
                continue

        if resp.status_code >= 400:
            logger.error("fetch failed %s -> %d", entry.url, resp.status_code)
            return FetchOutcome(
                entry=entry,
                status="error",
                http_status=resp.status_code,
                error=f"HTTP {resp.status_code}",
            )

        body = resp.text
        sha = hashlib.sha256(body.encode("utf-8", errors="ignore")).hexdigest()

        unchanged = (
            html_path.exists()
            and prior_meta.get("sha256") == sha
            and not force
        )
        if not unchanged:
            html_path.write_text(body, encoding="utf-8")

        meta = {
            "url": entry.url,
            "final_url": str(resp.url),
            "http_status": resp.status_code,
            "content_type": resp.headers.get("content-type", ""),
            "content_length": len(body),
            "etag": resp.headers.get("etag"),
            "last_modified": resp.headers.get("last-modified"),
            "sha256": sha,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "last_checked": datetime.now(timezone.utc).isoformat(),
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
        _write_meta(meta_path, meta)

        return FetchOutcome(
            entry=entry,
            status="cached" if unchanged else "fetched",
            http_status=resp.status_code,
            html_path=html_path,
            meta_path=meta_path,
        )

    return FetchOutcome(entry=entry, status="error", error=last_error or "unknown fetch error")


def build_client() -> httpx.Client:
    return httpx.Client(
        timeout=REQUEST_TIMEOUT,
        follow_redirects=True,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        },
    )


def build_limiter() -> _RateLimiter:
    return _RateLimiter(MIN_SECONDS_BETWEEN_HOST_REQUESTS)
