"""End-to-end acceptance test against a running /search endpoint.

Hits the live FastAPI server and records, per query:
  - top result title / source / course_code / content_kind
  - whether license, rubric, integration tips appear
  - any obvious ranking issue (top-1 wrong course for bare-code query)

Also runs:
  - one nonsense query
  - one repeated query (verifies cache_hit via debug=true)

Usage (from backend/, with uvicorn running on :8000):
    python -m scripts.acceptance_demo
"""

from __future__ import annotations

import json
import sys
import time
from typing import Any, Dict, List, Tuple

import httpx

API = "http://127.0.0.1:8000"
TIMEOUT = 60.0

REQUIRED_COURSES: List[Tuple[str, str]] = [
    ("ARTS 1100", "ARTS 1100"),
    ("ENGL 1101", "ENGL 1101"),
    ("ENGL 1102", "ENGL 1102"),
    ("HIST 2111", "HIST 2111"),
    ("HIST 2112", "HIST 2112"),
    ("ITEC 1001", "ITEC 1001"),
    ("BIOL 1101K", "BIOL 1101K"),
    ("BIOL 1102", "BIOL 1102"),
]

NATURAL_QUERIES: List[Tuple[str, str]] = [
    ("ARTS 1100", "art appreciation visual arts introduction"),
    ("ENGL 1101", "first-year english composition writing rhetoric"),
    ("ENGL 1102", "literature and composition literary analysis"),
    ("HIST 2111", "united states history colonial era to 1877"),
    ("HIST 2112", "united states history since 1877 twentieth century"),
    ("ITEC 1001", "introduction to computing principles information technology"),
    ("BIOL 1101K", "introductory biology molecules cells"),
    ("BIOL 1102", "biology organisms ecology ecosystems"),
]


def _post_search(client: httpx.Client, query: str, *, grounded: bool = True, debug: bool = True) -> Dict[str, Any]:
    resp = client.post(
        f"{API}/search",
        json={"query": query, "grounded": grounded, "top_k": 5, "debug": debug},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def _row(label: str, query: str, expected_course: str, data: Dict[str, Any]) -> Dict[str, Any]:
    results = data.get("results") or []
    top = results[0] if results else {}
    license_info = top.get("license") or {}
    rubric = top.get("rubric_evaluation") or {}
    tips = top.get("integration_tips") or []
    debug = data.get("_debug") or data.get("debug") or {}

    has_license = bool(license_info.get("status")) and bool(license_info.get("details"))
    has_rubric = any(
        isinstance(v, dict) and v.get("basis") and v.get("basis") != "unavailable"
        for v in rubric.values()
    )
    has_tips = len(tips) > 0
    top_course = (top.get("course_code") or "").upper()
    ranking_issue = ""
    if expected_course and top_course != expected_course.upper() and top.get("source"):
        ranking_issue = f"top-1 is {top_course or '-'}, expected {expected_course}"

    return {
        "label": label,
        "query": query,
        "expected": expected_course,
        "n_results": len(results),
        "top_title": top.get("title", ""),
        "top_source": top.get("source", ""),
        "top_course": top_course,
        "top_content_kind": top.get("content_kind", "extracted"),
        "license_visible": has_license,
        "rubric_visible": has_rubric,
        "tips_visible": has_tips,
        "ranking_issue": ranking_issue,
        "evaluation_mode": debug.get("evaluation_mode", ""),
        "cache_hit": debug.get("cache_hit", False),
        "fallback_used": debug.get("fallback_used", False),
        "summary_present": bool(data.get("summary", "").strip()),
        "warnings": data.get("warnings") or [],
        "errors": data.get("errors") or [],
    }


def _print_table(rows: List[Dict[str, Any]]) -> None:
    print("\n" + "=" * 110)
    print(
        f"{'LABEL':<26} {'TOP COURSE':<10} {'KIND':<18} {'LIC':<4} {'RUB':<4} {'TIP':<4} {'CACHE':<5} {'MODE':<11}  ISSUE"
    )
    print("-" * 110)
    for r in rows:
        kind = r["top_content_kind"][:18]
        mode = (r["evaluation_mode"] or "")[:11]
        issue = r["ranking_issue"][:80]
        print(
            f"{r['label']:<26} {r['top_course']:<10} {kind:<18} "
            f"{'Y' if r['license_visible'] else '-':<4} "
            f"{'Y' if r['rubric_visible'] else '-':<4} "
            f"{'Y' if r['tips_visible'] else '-':<4} "
            f"{'Y' if r['cache_hit'] else '-':<5} "
            f"{mode:<11}  {issue}"
        )


def main() -> int:
    rows: List[Dict[str, Any]] = []

    with httpx.Client() as client:
        # Required course set — bare code query
        for course, query in REQUIRED_COURSES:
            data = _post_search(client, query)
            rows.append(_row(f"code: {course}", query, course, data))

        # Required course set — natural query
        for course, query in NATURAL_QUERIES:
            data = _post_search(client, query)
            rows.append(_row(f"nat:  {course}", query, course, data))

        # Nonsense query
        data = _post_search(client, "asdfqwer xyzzy plugh")
        rows.append(_row("nonsense", "asdfqwer xyzzy plugh", "", data))

        # Cache hit: repeat the first required-course query
        repeat_query = REQUIRED_COURSES[0][1]
        # warm
        _post_search(client, repeat_query)
        # second call should hit cache
        data = _post_search(client, repeat_query)
        rows.append(_row("repeat (cache)", repeat_query, REQUIRED_COURSES[0][0], data))

        # Top result detail dump for each course (handy for the demo)
        print("\n" + "=" * 110)
        print(" PER-COURSE TOP RESULT DETAIL")
        print("=" * 110)
        for course, query in REQUIRED_COURSES:
            print(f"\n[{course}]  q={query!r}")
            data = _post_search(client, query)
            results = data.get("results") or []
            if not results:
                print("  (no results)")
                continue
            for i, r in enumerate(results[:3]):
                print(
                    f"  #{i + 1}  {r.get('course_code', ''):<10}  "
                    f"{r.get('source', ''):<22}  kind={r.get('content_kind', '')}"
                )
                print(f"        title: {r.get('title', '')}")
                lic = r.get('license') or {}
                print(
                    f"        license: status={lic.get('status', '')}  "
                    f"details={lic.get('details', '')[:80]}"
                )
                tips = r.get('integration_tips') or []
                if tips:
                    print(f"        tip[0]: {tips[0][:140]}")
                desc = (r.get('description') or '').strip().replace('\n', ' ')
                print(f"        desc: {desc[:140]}")

    _print_table(rows)

    # Failure summary by priority
    high: List[str] = []
    med: List[str] = []
    low: List[str] = []
    for r in rows:
        if r["label"].startswith("code:"):
            if r["ranking_issue"]:
                high.append(f"{r['label']} -- {r['ranking_issue']}")
            if not r["license_visible"]:
                med.append(f"{r['label']} -- license missing")
            if not r["tips_visible"]:
                med.append(f"{r['label']} -- no integration tip")
            if r["top_content_kind"] != "metadata_reference" and not r["rubric_visible"]:
                low.append(f"{r['label']} -- no rubric basis (LLM evaluation may have failed)")
        if r["label"] == "nonsense" and r["n_results"] > 0:
            med.append("nonsense query returned results above threshold")

    print("\n" + "=" * 110)
    print(" FAILURE SUMMARY BY PRIORITY")
    print("=" * 110)
    for level, items in (("HIGH", high), ("MEDIUM", med), ("LOW", low)):
        print(f"\n{level}:")
        if not items:
            print("  (none)")
        else:
            for it in items:
                print(f"  - {it}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
