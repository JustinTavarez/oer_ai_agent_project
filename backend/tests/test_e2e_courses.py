"""End-to-end tests for /search against all 8 required courses.

Requires:
  - Backend running on localhost:8000
  - LM Studio running with embedding + chat models
  - ChromaDB seeded

Run:
    python -m tests.test_e2e_courses

Not a pytest file -- run standalone only.
"""
# ruff: noqa
# pytest: skip_file

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

SEARCH_URL = "http://localhost:8000/search"

COURSES = [
    ("ARTS 1100", "art appreciation visual arts introduction"),
    ("ENGL 1101", "first-year composition writing course"),
    ("ENGL 1102", "literature and composition literary analysis"),
    ("HIST 2111", "US history to 1877 American history"),
    ("HIST 2112", "US history since 1877 modern America"),
    ("ITEC 1001", "introduction to computer science information technology"),
    ("BIOL 1101K", "biology molecules and cells introductory"),
    ("BIOL 1102", "biology organisms ecosystems ecology"),
]

REQUIRED_FIELDS = {"query", "timestamp", "log_id", "summary", "results", "warnings", "errors"}
RESOURCE_FIELDS = {
    "resource_id", "title", "description", "source", "url", "course_code",
    "relevance", "license", "integration_tips", "rubric_evaluation", "warnings",
}
RUBRIC_CATEGORIES = {
    "relevance_and_comprehensiveness", "interactivity_and_engagement",
    "pedagogical_soundness", "licensing_clarity", "accessibility_compliance",
    "modularity_and_adaptability", "supplementary_resources",
}

SEP = "-" * 60


async def check_course(client: httpx.AsyncClient, course_code: str, query: str, grounded: bool) -> dict:
    result = {"course": course_code, "grounded": grounded, "passed": True, "issues": []}

    payload = {"query": query, "top_k": 5, "grounded": grounded}
    try:
        resp = await client.post(SEARCH_URL, json=payload, timeout=120.0)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        result["passed"] = False
        result["issues"].append(f"Request failed: {e}")
        return result

    missing_top = REQUIRED_FIELDS - set(data.keys())
    if missing_top:
        result["passed"] = False
        result["issues"].append(f"Missing top-level fields: {missing_top}")

    if not data.get("log_id"):
        result["issues"].append("log_id is empty")
    if not data.get("timestamp"):
        result["issues"].append("timestamp is empty")

    results = data.get("results", [])
    result["result_count"] = len(results)

    if len(results) == 0:
        result["passed"] = False
        result["issues"].append("No results returned")
        return result

    for i, res in enumerate(results):
        missing_res = RESOURCE_FIELDS - set(res.keys())
        if missing_res:
            result["issues"].append(f"Result {i} missing fields: {missing_res}")

        if not res.get("title"):
            result["issues"].append(f"Result {i} has empty title")

        lic = res.get("license", {})
        if not isinstance(lic, dict) or "status" not in lic:
            result["issues"].append(f"Result {i} missing license.status")

        rel = res.get("relevance", {})
        if not isinstance(rel, dict) or "score" not in rel:
            result["issues"].append(f"Result {i} missing relevance.score")

        rubric = res.get("rubric_evaluation", {})
        if isinstance(rubric, dict):
            missing_cat = RUBRIC_CATEGORIES - set(rubric.keys())
            if missing_cat:
                result["issues"].append(f"Result {i} missing rubric categories: {missing_cat}")
            for cat_key, cat_val in rubric.items():
                if isinstance(cat_val, dict):
                    if "score" not in cat_val or "basis" not in cat_val:
                        result["issues"].append(f"Result {i} rubric '{cat_key}' missing score/basis")
        else:
            result["issues"].append(f"Result {i} rubric_evaluation is not a dict")

    if grounded and not data.get("summary"):
        result["issues"].append("Grounded response has empty summary")

    if result["issues"]:
        blocking = [i for i in result["issues"] if "missing fields" in i.lower() or "no results" in i.lower()]
        if blocking:
            result["passed"] = False

    return result


async def main():
    print(f"\n{'='*60}")
    print("  E2E Course Search Tests")
    print(f"{'='*60}")

    async with httpx.AsyncClient() as client:
        try:
            health = await client.get("http://localhost:8000/health", timeout=5.0)
            health.raise_for_status()
            print(f"  Backend: OK  |  LLM: {health.json().get('lm_studio', 'unknown')}")
        except Exception as e:
            print(f"  Backend unreachable: {e}")
            sys.exit(1)

        all_results = []
        for course_code, query in COURSES:
            print(f"\n{SEP}")
            print(f"  Testing: {course_code}")
            print(f"  Query: {query}")

            non_grounded = await check_course(client, course_code, query, grounded=False)
            status_ng = "PASS" if non_grounded["passed"] else "FAIL"
            print(f"  Non-grounded: [{status_ng}]  results={non_grounded.get('result_count', 0)}")
            for issue in non_grounded.get("issues", []):
                print(f"    ! {issue}")

            grounded_res = await check_course(client, course_code, query, grounded=True)
            status_g = "PASS" if grounded_res["passed"] else "FAIL"
            print(f"  Grounded:     [{status_g}]  results={grounded_res.get('result_count', 0)}")
            for issue in grounded_res.get("issues", []):
                print(f"    ! {issue}")

            all_results.append((course_code, non_grounded, grounded_res))

    print(f"\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")

    all_pass = True
    for course_code, ng, g in all_results:
        ng_s = "PASS" if ng["passed"] else "FAIL"
        g_s = "PASS" if g["passed"] else "FAIL"
        print(f"  {course_code:12s}  non-grounded=[{ng_s}]  grounded=[{g_s}]")
        if not ng["passed"] or not g["passed"]:
            all_pass = False

    overall = "PASS" if all_pass else "FAIL"
    print(f"\n  OVERALL: [{overall}]")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    asyncio.run(main())
