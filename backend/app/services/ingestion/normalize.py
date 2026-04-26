"""Turn raw fetched HTML + manifest metadata into normalized records.

Writes one JSON per line to data/normalized/records.jsonl. Parse failures
are appended to data/normalized/parse_failures.jsonl with a reason.

Unified record schema (required by downstream seeder):
  id, title, course_code, source, term, institution, license, license_url,
  resource_type, url, text
Optional (carried through when present on manifest):
  notes, mapping_rationale, subject_area
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from app.services.ingestion.parsers import ggc_simple_syllabus as ggc_parser
from app.services.ingestion.parsers import openalg as openalg_parser

logger = logging.getLogger(__name__)


@dataclass
class NormalizedRecord:
    id: str
    title: str
    course_code: str
    source: str
    term: str
    institution: str
    license: str
    license_url: str
    resource_type: str
    url: str
    text: str
    notes: str = ""
    mapping_rationale: str = ""
    subject_area: str = ""
    # "extracted" = body text comes from the actual fetched syllabus / textbook.
    # "metadata_reference" = body text is a synthetic stub built from the
    # manifest fields (course code, title, term, section, CRN, URL). Used for
    # GGC Simple Syllabus entries because the public site is a JS-rendered
    # SPA with no server-side parseable artifact. The chat/UI layer should
    # surface these as "reference link only — visit the URL for the full
    # syllabus" rather than treat them as authoritative content.
    content_kind: str = "extracted"


@dataclass
class ParseFailure:
    url: str
    source: str
    course_code: str
    reason: str
    html_path: str = ""


@dataclass
class NormalizeResult:
    records: List[NormalizedRecord] = field(default_factory=list)
    failures: List[ParseFailure] = field(default_factory=list)


def record_id(source: str, url: str) -> str:
    return hashlib.sha1(f"{source}|{url}".encode("utf-8")).hexdigest()[:16]


def normalize_from_raw(raw_root: Path) -> NormalizeResult:
    """Walk data/raw/{openalg,ggc_syllabi}/ and produce normalized records.

    Each raw HTML file has a sibling .meta.json (written by the fetcher)
    that carries the manifest fields we need to stamp onto the record.
    """
    result = NormalizeResult()

    for source_dir, parser_name in (
        ("openalg", "openalg"),
        ("ggc_syllabi", "ggc"),
    ):
        dir_path = raw_root / source_dir
        if not dir_path.exists():
            logger.info("no raw dir yet: %s", dir_path)
            continue

        for meta_file in sorted(dir_path.glob("*.meta.json")):
            html_file = meta_file.with_suffix("").with_suffix(".html")
            pdf_file = meta_file.with_suffix("").with_suffix(".pdf")

            html_exists = html_file.exists()
            pdf_exists = pdf_file.exists()

            # GGC routinely produces PDF-only artifacts because the HTML page
            # is a JS-rendered SPA shell. Only treat missing-HTML as a failure
            # when there is also no PDF to fall back to.
            if not html_exists and not pdf_exists:
                result.failures.append(ParseFailure(
                    url=_safe_load_url(meta_file),
                    source=_safe_load_source(meta_file),
                    course_code=_safe_load_course(meta_file),
                    reason="missing_html_sibling",
                    html_path=str(html_file),
                ))
                continue

            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            html = html_file.read_text(encoding="utf-8", errors="replace") if html_exists else ""
            pdf_bytes = pdf_file.read_bytes() if pdf_exists else b""

            try:
                record = _normalize_one(meta, html, parser_name, pdf_bytes=pdf_bytes)
            except Exception as exc:  # noqa: BLE001 - report and continue
                logger.exception("normalize failed for %s", meta.get("url"))
                result.failures.append(ParseFailure(
                    url=meta.get("url", ""),
                    source=meta.get("source", ""),
                    course_code=meta.get("course_code", ""),
                    reason=f"exception: {exc}",
                    html_path=str(html_file),
                ))
                continue

            if record is None:
                result.failures.append(ParseFailure(
                    url=meta.get("url", ""),
                    source=meta.get("source", ""),
                    course_code=meta.get("course_code", ""),
                    reason="unusable_parse_output",
                    html_path=str(html_file),
                ))
                continue

            result.records.append(record)

    return result


def _safe_load_url(meta_file: Path) -> str:
    try:
        return json.loads(meta_file.read_text(encoding="utf-8")).get("url", "")
    except Exception:
        return ""


def _safe_load_source(meta_file: Path) -> str:
    try:
        return json.loads(meta_file.read_text(encoding="utf-8")).get("source", "")
    except Exception:
        return ""


def _safe_load_course(meta_file: Path) -> str:
    try:
        return json.loads(meta_file.read_text(encoding="utf-8")).get("course_code", "")
    except Exception:
        return ""


def _normalize_one(
    meta: Dict,
    html: str,
    parser_name: str,
    pdf_bytes: bytes = b"",
) -> Optional[NormalizedRecord]:
    source = meta.get("source", "")
    url = meta.get("url", "")
    course_code = meta.get("course_code", "")
    manifest_title = meta.get("title", "")
    manifest_term = meta.get("term", "")
    resource_type = meta.get("resource_type", "")

    if parser_name == "openalg":
        parsed = openalg_parser.parse(html)
        title = manifest_title or parsed.title
        term = manifest_term
        institution = parsed.institution
        license_str = parsed.license
        license_url = parsed.license_url
        text = parsed.text()
    elif parser_name == "ggc":
        # GGC's public site is a JS-rendered Angular SPA with no server-side
        # parseable artifact (no PDF endpoint, no SEO HTML, no JSON state).
        # We try PDF then HTML; if both yield nothing usable we fall back to
        # a metadata-only reference record so the URL is still indexed and
        # surfaced in retrieval (clearly marked content_kind="metadata_reference").
        parsed = None
        if pdf_bytes:
            parsed = ggc_parser.parse_pdf_text(pdf_bytes)
            if not parsed.usable():
                parsed = None
        if parsed is None and html:
            parsed = ggc_parser.parse(html)
            if not parsed.usable():
                parsed = None
        if parsed is None:
            return _build_ggc_metadata_record(meta)
        title = manifest_title or parsed.title
        term = parsed.term or manifest_term
        institution = parsed.institution or "Georgia Gwinnett College"
        license_str = parsed.license
        license_url = parsed.license_url
        text = parsed.text()
    else:
        raise ValueError(f"unknown parser: {parser_name}")

    if not text or len(text) < 120:
        return None

    return NormalizedRecord(
        id=record_id(source, url),
        title=title,
        course_code=course_code,
        source=source,
        term=term,
        institution=institution,
        license=license_str,
        license_url=license_url,
        resource_type=resource_type,
        url=url,
        text=text,
        notes=meta.get("notes", ""),
        mapping_rationale=meta.get("mapping_rationale", ""),
        subject_area=meta.get("subject_area", ""),
        content_kind="extracted",
    )


def _build_ggc_metadata_record(meta: Dict) -> Optional[NormalizedRecord]:
    """Synthesize a metadata-only reference record for a GGC entry.

    Used when the GGC HTML and PDF both fail to yield parseable content
    (which is the common case because the GGC public site is a JS-rendered
    Angular SPA). The record is explicitly marked content_kind="metadata_reference"
    so downstream surfaces can disclaim it as a reference link rather than
    full syllabus content.
    """
    source = meta.get("source", "")
    url = meta.get("url", "")
    course_code = (meta.get("course_code") or "").strip()
    title = (meta.get("title") or "").strip()
    term = (meta.get("term") or "").strip()
    notes = (meta.get("notes") or "").strip()
    resource_type = meta.get("resource_type", "")

    if not url or not course_code:
        return None

    lines = [
        "GGC Simple Syllabus reference entry (metadata only).",
        "",
        f"Course: {course_code}{' - ' + title if title else ''}",
    ]
    if term:
        lines.append(f"Term: {term}")
    if notes:
        lines.append(f"Section / notes: {notes}")
    lines.extend([
        "Institution: Georgia Gwinnett College",
        f"Public syllabus URL: {url}",
        "",
        "This record is a reference link to a Georgia Gwinnett College Simple",
        "Syllabus page. The full instructor-published syllabus body text is",
        "rendered client-side by a JavaScript single-page application and is",
        "not available server-side without a headless browser. Use the URL",
        "above to view the official syllabus directly. This entry is included",
        "so the agent can cite a real, instructor-published GGC reference for",
        "this course and term; for textbook content, prefer the matching Open",
        "ALG resources in the same course.",
    ])
    text = "\n".join(lines)

    return NormalizedRecord(
        id=record_id(source, url),
        title=title or f"{course_code} ({term or 'GGC reference'})",
        course_code=course_code,
        source=source,
        term=term,
        institution="Georgia Gwinnett College",
        license="",
        license_url="",
        resource_type=resource_type or "syllabus",
        url=url,
        text=text,
        notes=notes,
        mapping_rationale=meta.get("mapping_rationale", ""),
        subject_area=meta.get("subject_area", ""),
        content_kind="metadata_reference",
    )


def write_records(records: Iterable[NormalizedRecord], out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out_path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(asdict(r), ensure_ascii=False))
            f.write("\n")
            n += 1
    return n


def write_failures(failures: Iterable[ParseFailure], out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out_path.open("w", encoding="utf-8") as f:
        for fail in failures:
            f.write(json.dumps(asdict(fail), ensure_ascii=False))
            f.write("\n")
            n += 1
    return n


def load_records(path: Path) -> List[Dict]:
    if not path.exists():
        return []
    out: List[Dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out
