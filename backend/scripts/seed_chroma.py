"""Seed ChromaDB with sample OER data.

Run from the backend/ directory:
    python -m scripts.seed_chroma
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.ingest import ingest_records, load_sample_data

DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "sample_oer.json"


async def main() -> None:
    if not DATA_PATH.exists():
        print(f"Error: data file not found at {DATA_PATH}")
        sys.exit(1)

    print(f"Loading sample data from {DATA_PATH} ...")
    records = load_sample_data(str(DATA_PATH))
    print(f"Found {len(records)} records.")

    print("Ingesting records (chunking + embedding + upsert) ...")
    chunk_count = await ingest_records(records)
    print(f"Done. Ingested {chunk_count} chunks into ChromaDB.")


if __name__ == "__main__":
    asyncio.run(main())
