"""Manifest loader/validator for the real-data ingestion pipeline.

Manifests are YAML files (lists of records) describing public URLs to fetch.
Validation is strict on required fields and enum values; unknown keys are
warned about, never silently dropped.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterable, List, Optional

import yaml

logger = logging.getLogger(__name__)

REQUIRED_COURSES = {
    "ARTS 1100",
    "ENGL 1101",
    "ENGL 1102",
    "HIST 2111",
    "HIST 2112",
    "ITEC 1001",
    "BIOL 1101K",
    "BIOL 1102",
}

ALLOWED_SOURCES = {"GGC Simple Syllabus", "Open ALG"}
ALLOWED_RESOURCE_TYPES = {"syllabus", "textbook", "project"}
ALLOWED_TERMS = {"", "Fall 2025", "Spring 2026"}

REQUIRED_FIELDS = ("course_code", "source", "url", "resource_type")
OPTIONAL_FIELDS = ("title", "term", "notes", "mapping_rationale", "subject_area")
ALL_FIELDS = set(REQUIRED_FIELDS) | set(OPTIONAL_FIELDS)

TODO_SENTINEL = "TODO"


@dataclass
class ManifestEntry:
    course_code: str
    source: str
    url: str
    resource_type: str
    title: str = ""
    term: str = ""
    notes: str = ""
    mapping_rationale: str = ""
    subject_area: str = ""

    def is_todo(self) -> bool:
        return not self.url or self.url.strip().upper() == TODO_SENTINEL

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ManifestLoadResult:
    entries: List[ManifestEntry] = field(default_factory=list)
    skipped_todo: List[ManifestEntry] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def load_manifest(path: str | Path) -> ManifestLoadResult:
    """Load and validate a manifest YAML file.

    Returns a ManifestLoadResult with fetchable entries, TODO-skipped entries,
    and a list of human-readable error strings. Never raises on bad rows —
    returns them in errors so the caller can print all problems at once.
    """
    p = Path(path)
    result = ManifestLoadResult()

    if not p.exists():
        result.errors.append(f"manifest not found: {p}")
        return result

    try:
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        result.errors.append(f"YAML parse error in {p}: {exc}")
        return result

    if raw is None:
        return result
    if not isinstance(raw, list):
        result.errors.append(f"manifest root must be a YAML list; got {type(raw).__name__}")
        return result

    seen_urls: set[str] = set()

    for idx, row in enumerate(raw):
        ctx = f"{p.name}[{idx}]"

        if not isinstance(row, dict):
            result.errors.append(f"{ctx}: row is not a mapping")
            continue

        unknown = set(row.keys()) - ALL_FIELDS
        if unknown:
            logger.warning("%s: ignoring unknown keys: %s", ctx, sorted(unknown))

        missing = [k for k in REQUIRED_FIELDS if k not in row]
        if missing:
            result.errors.append(f"{ctx}: missing required fields: {missing}")
            continue

        course_code = str(row["course_code"]).strip()
        source = str(row["source"]).strip()
        url = str(row["url"]).strip()
        resource_type = str(row["resource_type"]).strip()

        if course_code not in REQUIRED_COURSES:
            result.errors.append(
                f"{ctx}: course_code {course_code!r} not in required set {sorted(REQUIRED_COURSES)}"
            )
            continue
        if source not in ALLOWED_SOURCES:
            result.errors.append(
                f"{ctx}: source {source!r} not in {sorted(ALLOWED_SOURCES)}"
            )
            continue
        if resource_type not in ALLOWED_RESOURCE_TYPES:
            result.errors.append(
                f"{ctx}: resource_type {resource_type!r} not in {sorted(ALLOWED_RESOURCE_TYPES)}"
            )
            continue

        term = str(row.get("term", "") or "").strip()
        if term not in ALLOWED_TERMS:
            logger.warning(
                "%s: term %r is not in the preferred set %s; accepting as-is",
                ctx, term, sorted(ALLOWED_TERMS),
            )

        entry = ManifestEntry(
            course_code=course_code,
            source=source,
            url=url,
            resource_type=resource_type,
            title=str(row.get("title", "") or "").strip(),
            term=term,
            notes=str(row.get("notes", "") or "").strip(),
            mapping_rationale=str(row.get("mapping_rationale", "") or "").strip(),
            subject_area=str(row.get("subject_area", "") or "").strip(),
        )

        if entry.is_todo():
            result.skipped_todo.append(entry)
            continue

        if url in seen_urls:
            logger.warning("%s: duplicate url %r; skipping dup", ctx, url)
            continue
        seen_urls.add(url)

        result.entries.append(entry)

    return result


def load_manifests(paths: Iterable[str | Path]) -> ManifestLoadResult:
    """Load multiple manifests; merge entries/errors into a single result."""
    merged = ManifestLoadResult()
    seen_urls: set[str] = set()
    for p in paths:
        r = load_manifest(p)
        merged.errors.extend(r.errors)
        merged.skipped_todo.extend(r.skipped_todo)
        for e in r.entries:
            if e.url in seen_urls:
                logger.warning("duplicate url across manifests: %s", e.url)
                continue
            seen_urls.add(e.url)
            merged.entries.append(e)
    return merged
