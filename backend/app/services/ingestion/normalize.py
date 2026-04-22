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
            if not html_file.exists():
                result.failures.append(ParseFailure(
                    url=_safe_load_url(meta_file),
                    source=_safe_load_source(meta_file),
                    course_code=_safe_load_course(meta_file),
                    reason="missing_html_sibling",
                    html_path=str(html_file),
                ))
                continue

            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            html = html_file.read_text(encoding="utf-8", errors="replace")

            try:
                record = _normalize_one(meta, html, parser_name)
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


def _normalize_one(meta: Dict, html: str, parser_name: str) -> Optional[NormalizedRecord]:
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
        parsed = ggc_parser.parse(html)
        if not parsed.usable():
            return None
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
