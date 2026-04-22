"""Search validation against the real-data collection.

Usage (from backend/):
    python -m scripts.validate_search

For each of the 8 required courses, runs two queries (course code and a
natural-language subject phrase), prints the top-5 hits, and reports a
report-only weakness summary. There is no hard distance cutoff yet — once
we have enough real data we'll calibrate a threshold.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from statistics import median
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.chroma_client import get_real_collection  # noqa: E402
from app.services.embeddings import close_client, get_embedding  # noqa: E402
from app.services.ingestion.manifest import REQUIRED_COURSES  # noqa: E402

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


async def _run_query(collection, query: str) -> List[Dict]:
    q_embed = await get_embedding(query)
    res = collection.query(
        query_embeddings=[q_embed],
        n_results=TOP_K,
        include=["documents", "metadatas", "distances"],
    )
    ids = res.get("ids", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0]
    hits = []
    for i in range(len(ids)):
        m = metas[i] if i < len(metas) else {}
        d = dists[i] if i < len(dists) else None
        hits.append({
            "id": ids[i],
            "title": m.get("title", ""),
            "source": m.get("source", ""),
            "course_code": m.get("course_code", ""),
            "distance": d,
        })
    return hits


def _print_hits(label: str, hits: List[Dict]) -> None:
    print(f"\n  [{label}]")
    if not hits:
        print("    (no results)")
        return
    for h in hits:
        dist = h["distance"]
        dist_str = f"{dist:.4f}" if isinstance(dist, (int, float)) else "n/a"
        print(f"    d={dist_str}  {h['course_code']:10s}  {h['source']:22s}  {h['title']}")


async def main() -> int:
    collection = get_real_collection()
    print(f"collection: {collection.name}")

    weakness: List[str] = []

    for course in sorted(REQUIRED_COURSES):
        print(f"\n{SEPARATOR}\n  {course}\n{SEPARATOR}")
        q = COURSE_QUERIES[course]

        try:
            code_hits = await _run_query(collection, q["code"])
        except Exception as exc:  # noqa: BLE001
            print(f"  code query failed: {exc}")
            await close_client()
            return 2
        _print_hits(f"code query: {q['code']!r}", code_hits)

        nat_hits = await _run_query(collection, q["natural"])
        _print_hits(f"natural:    {q['natural']!r}", nat_hits)

        all_hits = code_hits + nat_hits
        distances = [h["distance"] for h in all_hits if isinstance(h["distance"], (int, float))]
        matched = [h for h in all_hits if (h["course_code"] or "").upper() == course.upper()]

        if distances:
            print(
                f"\n  distance report: best={min(distances):.4f}  "
                f"median={median(distances):.4f}  worst={max(distances):.4f}"
            )
        print(f"  matching course_code in top-{TOP_K}x2: {len(matched)}")
        if not matched:
            weakness.append(f"{course}: no hit with matching course_code in combined top-{TOP_K}x2")
        elif distances and min(distances) > 0.6:
            weakness.append(
                f"{course}: best distance {min(distances):.4f} > 0.6 (weak match; not a failure)"
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
