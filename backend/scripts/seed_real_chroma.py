"""Seed the real-data Chroma collection (oer_resources_real).

Usage (from backend/):
    python -m scripts.seed_real_chroma

Always writes to get_real_collection() regardless of CHROMA_ACTIVE_COLLECTION.
To make the app/query layer *read* from the real collection, set
    CHROMA_ACTIVE_COLLECTION=oer_resources_real
in backend/.env (no code change required).
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.ingestion.seed_real import seed_real  # noqa: E402


async def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    project_root = Path(__file__).resolve().parent.parent.parent
    records_path = project_root / "data" / "normalized" / "records.jsonl"

    if not records_path.exists():
        print(f"error: {records_path} does not exist. Run parse_and_normalize first.")
        return 1

    summary = await seed_real(records_path)
    print(f"seed summary: {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
