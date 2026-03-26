"""Verify ChromaDB is seeded and retrieval works for all 8 required courses.

Run from the backend/ directory:
    python -m scripts.verify_chroma
"""

import asyncio
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.chroma_client import get_collection
from app.services.retrieval import search

REQUIRED_COURSES = [
    "ARTS 1100",
    "ENGL 1101",
    "ENGL 1102",
    "HIST 2111",
    "HIST 2112",
    "ITEC 1001",
    "BIOL 1101K",
    "BIOL 1102",
]

COURSE_QUERIES = {
    "ARTS 1100": {
        "code_query": "ARTS 1100",
        "natural": "art appreciation visual arts introduction",
        "subject": "art history and visual culture",
        "expected_titles_contain": ["art"],
    },
    "ENGL 1101": {
        "code_query": "ENGL 1101",
        "natural": "first-year composition writing course",
        "subject": "English composition and writing",
        "expected_titles_contain": ["writing", "composition", "english"],
    },
    "ENGL 1102": {
        "code_query": "ENGL 1102",
        "natural": "literature and composition literary analysis",
        "subject": "English literature and composition",
        "expected_titles_contain": ["literature", "composition", "english"],
    },
    "HIST 2111": {
        "code_query": "HIST 2111",
        "natural": "US history to 1877 American history survey",
        "subject": "United States history colonial to reconstruction",
        "expected_titles_contain": ["history", "1877"],
    },
    "HIST 2112": {
        "code_query": "HIST 2112",
        "natural": "US history since 1877 modern America",
        "subject": "United States history modern era",
        "expected_titles_contain": ["history", "1877"],
    },
    "ITEC 1001": {
        "code_query": "ITEC 1001",
        "natural": "introduction to computer science information technology",
        "subject": "computing and IT fundamentals",
        "expected_titles_contain": ["computer", "information", "technology"],
    },
    "BIOL 1101K": {
        "code_query": "BIOL 1101K",
        "natural": "biology molecules and cells introductory",
        "subject": "introductory biology molecular cellular",
        "expected_titles_contain": ["biology", "molecules", "cells"],
    },
    "BIOL 1102": {
        "code_query": "BIOL 1102",
        "natural": "biology organisms ecosystems ecology",
        "subject": "biology ecology and evolution",
        "expected_titles_contain": ["biology", "organisms", "ecosystems"],
    },
}

SEPARATOR = "-" * 70


def print_section(title: str) -> None:
    print(f"\n{SEPARATOR}")
    print(f"  {title}")
    print(SEPARATOR)


def check_metadata_completeness(collection) -> dict:
    """Check metadata field presence across all stored documents."""
    all_data = collection.get(include=["metadatas"])
    metadatas = all_data.get("metadatas", [])
    total = len(metadatas)

    fields_to_check = [
        "title", "source", "course_code", "url", "license",
        "resource_type", "subject", "term", "institution",
        "has_accessibility_info", "has_supplementary_materials",
    ]

    counts = {}
    for field in fields_to_check:
        present = sum(
            1 for m in metadatas
            if m.get(field) not in (None, "", False)
        )
        counts[field] = present

    return {"total": total, "field_counts": counts}


def check_course_coverage(collection) -> dict:
    """Check which course_codes are stored and their chunk counts."""
    all_data = collection.get(include=["metadatas"])
    metadatas = all_data.get("metadatas", [])
    course_counter = Counter(m.get("course_code", "") for m in metadatas)
    source_counter = Counter(m.get("source", "") for m in metadatas)
    return {
        "courses": dict(course_counter),
        "sources": dict(source_counter),
    }


def is_relevant_hit(hit: dict, course_code: str, expected_title_words: list[str]) -> bool:
    """Check if a retrieval hit is relevant to the target course."""
    if hit.get("course_code", "").upper() == course_code.upper():
        return True
    title_lower = hit.get("title", "").lower()
    return any(word.lower() in title_lower for word in expected_title_words)


async def test_course_retrieval(
    course_code: str,
    queries: dict,
    top_k: int = 3,
) -> dict:
    """Run three query types for a course and evaluate relevance."""
    result = {
        "course": course_code,
        "queries": {},
        "passed": True,
        "issues": [],
    }

    expected_words = queries["expected_titles_contain"]

    # Query 1: direct course code query
    try:
        hits = await search(query=queries["code_query"], top_k=top_k)
        top_hits = hits[:3]
        relevant = [h for h in top_hits if is_relevant_hit(h, course_code, expected_words)]
        result["queries"]["code_query"] = {
            "query": queries["code_query"],
            "result_count": len(hits),
            "top_3": [
                {"title": h["title"], "score": h["score"], "source": h["source"], "course_code": h["course_code"]}
                for h in top_hits
            ],
            "relevant_in_top_3": len(relevant),
        }
        if not relevant:
            result["passed"] = False
            result["issues"].append(f"code_query: no relevant result in top 3")
    except Exception as e:
        result["queries"]["code_query"] = {"error": str(e)}
        result["passed"] = False
        result["issues"].append(f"code_query failed: {e}")

    # Query 2: natural language query
    try:
        hits = await search(query=queries["natural"], top_k=top_k)
        top_hits = hits[:3]
        relevant = [h for h in top_hits if is_relevant_hit(h, course_code, expected_words)]
        result["queries"]["natural"] = {
            "query": queries["natural"],
            "result_count": len(hits),
            "top_3": [
                {"title": h["title"], "score": h["score"], "source": h["source"], "course_code": h["course_code"]}
                for h in top_hits
            ],
            "relevant_in_top_3": len(relevant),
        }
        if not relevant:
            result["passed"] = False
            result["issues"].append(f"natural query: no relevant result in top 3")
    except Exception as e:
        result["queries"]["natural"] = {"error": str(e)}
        result["passed"] = False
        result["issues"].append(f"natural query failed: {e}")

    # Query 3: subject-style query
    try:
        hits = await search(query=queries["subject"], top_k=top_k)
        top_hits = hits[:3]
        relevant = [h for h in top_hits if is_relevant_hit(h, course_code, expected_words)]
        result["queries"]["subject"] = {
            "query": queries["subject"],
            "result_count": len(hits),
            "top_3": [
                {"title": h["title"], "score": h["score"], "source": h["source"], "course_code": h["course_code"]}
                for h in top_hits
            ],
            "relevant_in_top_3": len(relevant),
        }
        if not relevant:
            result["issues"].append(f"subject query: no relevant result in top 3 (non-blocking)")
    except Exception as e:
        result["queries"]["subject"] = {"error": str(e)}
        result["issues"].append(f"subject query failed: {e}")

    return result


async def main() -> None:
    summary = {
        "seed_success": False,
        "total_stored": 0,
        "course_coverage": {},
        "metadata_completeness": {},
        "retrieval_results": {},
        "overall_pass": True,
    }

    # --- 1. Collection stats ---
    print_section("1. CHROMADB COLLECTION STATS")
    try:
        collection = get_collection()
        count = collection.count()
        summary["total_stored"] = count
        summary["seed_success"] = count > 0
        print(f"  Collection name:  oer_resources")
        print(f"  Total documents:  {count}")
        if count == 0:
            print("\n  FAIL: ChromaDB is empty. Run seed_chroma.py first.")
            summary["overall_pass"] = False
            _print_summary(summary)
            sys.exit(1)
    except Exception as e:
        print(f"  FAIL: Could not connect to ChromaDB: {e}")
        summary["overall_pass"] = False
        _print_summary(summary)
        sys.exit(1)

    # --- 2. Course coverage ---
    print_section("2. COURSE COVERAGE")
    coverage = check_course_coverage(collection)
    summary["course_coverage"] = coverage["courses"]
    print(f"  Chunks per course_code:")
    for code in REQUIRED_COURSES:
        chunk_count = coverage["courses"].get(code, 0)
        status = "OK" if chunk_count > 0 else "MISSING"
        print(f"    {code:12s}  {chunk_count:3d} chunks  [{status}]")
        if chunk_count == 0:
            summary["overall_pass"] = False

    print(f"\n  Chunks per source:")
    for source, cnt in sorted(coverage["sources"].items()):
        print(f"    {source:20s}  {cnt:3d} chunks")

    missing = [c for c in REQUIRED_COURSES if coverage["courses"].get(c, 0) == 0]
    if missing:
        print(f"\n  FAIL: Missing courses: {', '.join(missing)}")

    # --- 3. Metadata completeness ---
    print_section("3. METADATA COMPLETENESS")
    meta = check_metadata_completeness(collection)
    total = meta["total"]
    summary["metadata_completeness"] = meta["field_counts"]
    print(f"  Total documents: {total}")
    print(f"  Field presence (non-empty/non-false):")
    for field, cnt in meta["field_counts"].items():
        pct = (cnt / total * 100) if total > 0 else 0
        flag = "OK" if pct > 50 else "LOW"
        print(f"    {field:30s}  {cnt:3d}/{total}  ({pct:5.1f}%)  [{flag}]")

    # --- 4. Retrieval tests ---
    print_section("4. RETRIEVAL TESTS (all 8 courses)")
    all_results = {}
    for course_code in REQUIRED_COURSES:
        queries = COURSE_QUERIES[course_code]
        result = await test_course_retrieval(course_code, queries)
        all_results[course_code] = result

        status = "PASS" if result["passed"] else "FAIL"
        print(f"\n  [{status}] {course_code}")

        for qtype in ["code_query", "natural", "subject"]:
            qdata = result["queries"].get(qtype, {})
            if "error" in qdata:
                print(f"    {qtype:12s}  ERROR: {qdata['error']}")
                continue
            top3 = qdata.get("top_3", [])
            relevant = qdata.get("relevant_in_top_3", 0)
            print(f"    {qtype:12s}  results={qdata.get('result_count', 0)}  relevant_in_top3={relevant}")
            for i, h in enumerate(top3):
                marker = "*" if is_relevant_hit(
                    h, course_code, queries["expected_titles_contain"]
                ) else " "
                print(f"      {marker} #{i+1}  score={h['score']:.4f}  [{h['source']}] {h['title']}")

        if result["issues"]:
            for issue in result["issues"]:
                print(f"    ! {issue}")

        if not result["passed"]:
            summary["overall_pass"] = False

    summary["retrieval_results"] = {
        code: res["passed"] for code, res in all_results.items()
    }

    # --- 5. Final summary ---
    _print_summary(summary)

    sys.exit(0 if summary["overall_pass"] else 1)


def _print_summary(summary: dict) -> None:
    print_section("5. FINAL SUMMARY")

    seed_status = "PASS" if summary["seed_success"] else "FAIL"
    print(f"  Seed success:      [{seed_status}]  ({summary['total_stored']} documents stored)")

    coverage = summary.get("course_coverage", {})
    covered = sum(1 for c in REQUIRED_COURSES if coverage.get(c, 0) > 0)
    cov_status = "PASS" if covered == len(REQUIRED_COURSES) else "FAIL"
    print(f"  Course coverage:   [{cov_status}]  {covered}/{len(REQUIRED_COURSES)} courses have chunks")

    meta = summary.get("metadata_completeness", {})
    total = summary["total_stored"]
    critical_fields = ["title", "source", "course_code", "license"]
    if total > 0 and meta:
        all_critical_ok = all(meta.get(f, 0) == total for f in critical_fields)
        meta_status = "PASS" if all_critical_ok else "WARN"
        print(f"  Metadata complete: [{meta_status}]  critical fields: {', '.join(critical_fields)}")
        for f in critical_fields:
            cnt = meta.get(f, 0)
            print(f"    {f:15s}  {cnt}/{total}")

    retrieval = summary.get("retrieval_results", {})
    if retrieval:
        print(f"  Retrieval per course:")
        for code in REQUIRED_COURSES:
            passed = retrieval.get(code)
            if passed is None:
                print(f"    {code:12s}  [SKIP]")
            elif passed:
                print(f"    {code:12s}  [PASS]")
            else:
                print(f"    {code:12s}  [FAIL]")

    overall = "PASS" if summary["overall_pass"] else "FAIL"
    print(f"\n  OVERALL: [{overall}]")
    if overall == "PASS":
        print("  ChromaDB is seeded and retrieval is verified. Ready for steps 9-18.")
    else:
        print("  Issues found. Review failures above before proceeding.")


if __name__ == "__main__":
    asyncio.run(main())
