"""Verify the oer_resources_real Chroma collection.

Usage (from backend/):
    python -m scripts.verify_real_chroma

Prints:
  - total chunks
  - total distinct documents (by metadata url)
  - distinct course_codes
  - distinct sources (should be exactly: GGC Simple Syllabus, Open ALG)
  - count by source
  - count by course_code
  - coverage matrix for the 8 required courses (has_syllabus / has_openalg)

Exits non-zero only if every required course is missing BOTH a syllabus
and an OpenALG resource — partial gaps are reported but not a failure.
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.chroma_client import get_real_collection  # noqa: E402
from app.services.ingestion.manifest import REQUIRED_COURSES  # noqa: E402

SEPARATOR = "-" * 70


def _section(title: str) -> None:
    print(f"\n{SEPARATOR}\n  {title}\n{SEPARATOR}")


def main() -> int:
    collection = get_real_collection()
    print(f"collection: {collection.name}")

    data = collection.get(include=["metadatas"])
    metas = data.get("metadatas", []) or []
    total_chunks = len(metas)

    urls = {m.get("url", "") for m in metas if m.get("url")}
    course_counter = Counter((m.get("course_code") or "") for m in metas)
    source_counter = Counter((m.get("source") or "") for m in metas)

    # doc-level counts (distinct urls) per course/source
    per_course_urls: dict[str, set[str]] = defaultdict(set)
    per_source_urls: dict[str, set[str]] = defaultdict(set)
    per_course_sources: dict[str, set[str]] = defaultdict(set)
    for m in metas:
        url = m.get("url") or ""
        cc = m.get("course_code") or ""
        src = m.get("source") or ""
        if url:
            per_course_urls[cc].add(url)
            per_source_urls[src].add(url)
            per_course_sources[cc].add(src)

    _section("Totals")
    print(f"total_chunks   = {total_chunks}")
    print(f"total_documents= {len(urls)}  (distinct urls in metadata)")
    print(f"distinct course_codes = {sorted(c for c in course_counter if c)}")
    print(f"distinct sources      = {sorted(s for s in source_counter if s)}")

    _section("Count by source (chunks | docs)")
    for src, count in sorted(source_counter.items()):
        docs = len(per_source_urls.get(src, set()))
        label = src or "(empty)"
        print(f"  {label:28s}  chunks={count:4d}  docs={docs:3d}")

    _section("Count by course_code (chunks | docs)")
    for cc, count in sorted(course_counter.items()):
        docs = len(per_course_urls.get(cc, set()))
        label = cc or "(empty)"
        print(f"  {label:12s}  chunks={count:4d}  docs={docs:3d}")

    # Per-course content_kind tally restricted to GGC syllabus rows so the
    # matrix correctly distinguishes 'ref' (metadata-only) from 'yes'
    # (extracted body text), regardless of Open ALG content_kind values.
    per_course_ggc_kinds: dict[str, set[str]] = defaultdict(set)
    for m in metas:
        cc = m.get("course_code") or ""
        src = m.get("source") or ""
        if cc and src == "GGC Simple Syllabus":
            per_course_ggc_kinds[cc].add(m.get("content_kind") or "extracted")

    _section("Coverage matrix (required courses)")
    all_missing = 0
    for course in sorted(REQUIRED_COURSES):
        sources = per_course_sources.get(course, set())
        ggc_kinds = per_course_ggc_kinds.get(course, set())
        has_syllabus = "GGC Simple Syllabus" in sources
        has_openalg = "Open ALG" in sources
        syllabus_label = "no "
        if has_syllabus:
            syllabus_label = (
                "ref"
                if ggc_kinds and "extracted" not in ggc_kinds
                else "yes"
            )
        flag = "OK" if (has_syllabus or has_openalg) else "MISSING"
        print(
            f"  {course:12s}  syllabus={syllabus_label}   "
            f"openalg={'yes' if has_openalg else 'no '}   {flag}"
        )
        if not (has_syllabus or has_openalg):
            all_missing += 1
    print("\n  (syllabus column: 'yes' = extracted body text, 'ref' = metadata-only GGC reference link, 'no ' = absent)")

    _section("Summary")
    print(f"required courses with at least one real resource: "
          f"{len(REQUIRED_COURSES) - all_missing}/{len(REQUIRED_COURSES)}")
    if all_missing == len(REQUIRED_COURSES):
        print("FAIL: every required course is missing real data.")
        return 1
    if all_missing:
        print(f"WARN: {all_missing} required course(s) have no data yet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
