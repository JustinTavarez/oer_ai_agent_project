"""Seed the real-data Chroma collection from normalized records.jsonl.

Uses the existing ``chunk_text`` helper (paragraph-aware, heading-preserving)
at a 700-char target with 80-char overlap, landing in the requested
500-800 char band. Always writes to ``get_real_collection()`` — never the
active/sample collection — so running this is safe regardless of the
``CHROMA_ACTIVE_COLLECTION`` env var.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List

from app.services.chroma_client import get_real_collection
from app.services.embeddings import get_embeddings
from app.services.ingest import chunk_text
from app.services.ingestion.normalize import load_records

logger = logging.getLogger(__name__)

REAL_CHUNK_MAX_CHARS = 700
EMBED_BATCH_SIZE = 32


async def seed_real(records_path: Path) -> Dict:
    records = load_records(records_path)
    if not records:
        return {"records": 0, "chunks": 0, "reason": "no records"}

    ids: List[str] = []
    docs: List[str] = []
    metas: List[Dict] = []

    for rec in records:
        text = rec.get("text", "") or ""
        chunks = chunk_text(text, max_chars=REAL_CHUNK_MAX_CHARS)
        for idx, chunk in enumerate(chunks):
            ids.append(f"{rec['id']}_chunk_{idx}")
            docs.append(chunk)
            metas.append({
                "title": rec.get("title", ""),
                "source": rec.get("source", ""),
                "course_code": rec.get("course_code", ""),
                "license": rec.get("license", ""),
                "license_url": rec.get("license_url", ""),
                "url": rec.get("url", ""),
                "chunk_index": idx,
                "resource_type": rec.get("resource_type", ""),
                "subject": rec.get("subject_area", ""),
                "term": rec.get("term", ""),
                "institution": rec.get("institution", ""),
                "dataset": "real",
                "notes": rec.get("notes", ""),
                "mapping_rationale": rec.get("mapping_rationale", ""),
                "content_kind": rec.get("content_kind", "extracted"),
                "has_accessibility_info": False,
                "has_supplementary_materials": False,
            })

    if not docs:
        return {"records": len(records), "chunks": 0, "reason": "no chunks produced"}

    all_embeddings: List[List[float]] = []
    for i in range(0, len(docs), EMBED_BATCH_SIZE):
        batch = docs[i:i + EMBED_BATCH_SIZE]
        embeds = await get_embeddings(batch)
        all_embeddings.extend(embeds)
        logger.info("embedded %d/%d chunks", min(i + EMBED_BATCH_SIZE, len(docs)), len(docs))

    collection = get_real_collection()
    collection.upsert(
        ids=ids,
        documents=docs,
        embeddings=all_embeddings,
        metadatas=metas,
    )

    return {
        "records": len(records),
        "chunks": len(ids),
        "collection": collection.name,
    }
