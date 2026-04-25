"""Search validation against the real-data collection.

Usage (from backend/):
    python -m scripts.validate_search

For each of the 8 required courses, runs two queries (course code and a
natural-language subject phrase) through the same retrieval path the
``/search`` API uses (course-code re-rank + over-fetch). Prints the
top-5 ranked results plus a report-only weakness summary.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from statistics import median
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.chroma_client import get_real_collection  # noqa: E402
from app.services.embeddings import close_client  # noqa: E402
from app.services.ingestion.manifest import REQUIRED_COURSES  # noqa: E402
from app.services.retrieval import search as pipeline_search  # noqa: E402

SEPARATOR = "-" * 70
TOP_K = 5

COURSE_QUERIES: Dict[str, Dict[str, str]] = {
    "ARTS 1100":  {"code": "ARTS 1100", "natural": "art appreciation visual arts introduction"},
    "ENGL 1101":  {"code": "ENGL 1101", "natural": "first-year english composition writing rhetoric"},
    "ENGL 1102":  {"code": "ENGL 1102", "natural": "literature and composition literary analysis"},
    "HIST 2111":  {"code": "HIST 2111", "natural": "united states history colonial era to 1877"},
    "HIST 2112":  {"code": "HIST 2112", "natural": "united states history since 1877 twentieth century"},
    "ITEC 1001":  {"code": "ITEC 1001", "natural": "introduction to computing principles information technology"},
    "BIOL 1101K": {"code": "BIOL 1101K", "natural": "introductory biology molecules cells"},
    "BIOL 1102":  {"code": "BIOL 1102", "natural": "biology organisms ecology ecosystems"},
}


async def _run_query(query: str) -> List[Dict]:
    """Run the live retrieval pipeline (Chroma + course-code re-rank)."""
    raw = await pipeline_search(query=query, top_k=TOP_K)
    out: List[Dict] = []
    for h in raw:
        meta = h.get("metadata", {}) or {}
        score = h.get("score", 0.0)
        raw_score = h.get("raw_score", score)
        out.append({
            "id": h.get("id", ""),
            "title": h.get("title", ""),
            "source": h.get("source", ""),
            "course_code": h.get("course_code", ""),
            "content_kind": meta.get("content_kind", "extracted"),
            # Show the boosted similarity so the report reflects what the
            # API returns. raw_distance is the un-boosted Chroma distance.
            "score": score,
            "raw_distance": round(max(0.0, 1.0 - raw_score), 4),
            "course_match": h.get("course_match", False),
        })
    return out


def _print_hits(label: str, hits: List[Dict]) -> None:
    print(f"\n  [{label}]")
    if not hits:
        print("    (no results)")
        return
    for h in hits:
        score = h.get("score", 0.0)
        raw_d = h.get("raw_distance")
        score_str = f"s={score:.4f}"
        raw_str = f"(raw_d={raw_d:.4f})" if isinstance(raw_d, (int, float)) else ""
        kind_tag = " [REF]" if h.get("content_kind") == "metadata_reference" else ""
        boost_tag = " [BOOST]" if h.get("course_match") else ""
        print(
            f"    {score_str} {raw_str}  {h['course_code']:10s}  "
            f"{h['source']:22s}{kind_tag}{boost_tag}  {h['title']}"
        )


async def main() -> int:
    collection = get_real_collection()
    print(f"collection: {collection.name}")

    weakness: List[str] = []

    for course in sorted(REQUIRED_COURSES):
        print(f"\n{SEPARATOR}\n  {course}\n{SEPARATOR}")
        q = COURSE_QUERIES[course]

        try:
            code_hits = await _run_query(q["code"])
        except Exception as exc:  # noqa: BLE001
            print(f"  code query failed: {exc}")
            await close_client()
            return 2
        _print_hits(f"code query: {q['code']!r}", code_hits)

        nat_hits = await _run_query(q["natural"])
        _print_hits(f"natural:    {q['natural']!r}", nat_hits)

        all_hits = code_hits + nat_hits
        scores = [h["score"] for h in all_hits if isinstance(h["score"], (int, float))]
        matched = [h for h in all_hits if (h["course_code"] or "").upper() == course.upper()]

        if scores:
            best_score = max(scores)
            print(
                f"\n  score report: best={best_score:.4f}  "
                f"median={median(scores):.4f}  worst={min(scores):.4f}"
            )
            top1_code = code_hits[0]["course_code"].upper() if code_hits else ""
            top1_nat = nat_hits[0]["course_code"].upper() if nat_hits else ""
            print(
                f"  top-1 (code query) course: {top1_code or '-'}    "
                f"top-1 (natural) course: {top1_nat or '-'}"
            )
        print(f"  matching course_code in top-{TOP_K}x2: {len(matched)}")

        # Weakness: top-1 of the bare-code query is not the target course.
        # Use the score (boosted) so we measure post-rerank behavior.
        if not matched:
            weakness.append(f"{course}: no hit with matching course_code in combined top-{TOP_K}x2")
        else:
            if code_hits and code_hits[0]["course_code"].upper() != course.upper():
                weakness.append(
                    f"{course}: bare-code query top-1 is "
                    f"{code_hits[0]['course_code']} (expected {course})"
                )

    print(f"\n{SEPARATOR}\n  Weakness summary (report-only)\n{SEPARATOR}")
    if weakness:
        for w in weakness:
            print(f"  - {w}")
    else:
        print("  no weaknesses flagged")

    await close_client()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
