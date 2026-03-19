import json
import re
from pathlib import Path

from app.services.chroma_client import get_collection
from app.services.embeddings import get_embeddings

DEFAULT_MAX_CHARS = 500
OVERLAP_CHARS = 50


def load_sample_data(path: str) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def chunk_text(text: str, max_chars: int = DEFAULT_MAX_CHARS) -> list[str]:
    """Split text into chunks using a paragraph-aware strategy.

    1. Split on double-newlines into paragraphs.
    2. Keep heading lines attached to the paragraph that follows.
    3. Merge short paragraphs until approaching max_chars.
    4. Fall back to character-based splitting with overlap for
       any single paragraph exceeding max_chars.
    """
    raw_blocks = re.split(r"\n{2,}", text.strip())
    if not raw_blocks:
        return [text.strip()] if text.strip() else []

    paragraphs: list[str] = []
    heading_prefix = ""
    for block in raw_blocks:
        block = block.strip()
        if not block:
            continue
        if block.startswith("#"):
            heading_prefix = block + "\n\n"
            continue
        if heading_prefix:
            block = heading_prefix + block
            heading_prefix = ""
        paragraphs.append(block)

    if heading_prefix:
        paragraphs.append(heading_prefix.strip())

    if not paragraphs:
        return [text.strip()] if text.strip() else []

    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if len(para) > max_chars:
            if current:
                chunks.append(current.strip())
                current = ""
            chunks.extend(_split_long_block(para, max_chars))
            continue

        if current and len(current) + len(para) + 2 > max_chars:
            chunks.append(current.strip())
            current = para
        else:
            current = f"{current}\n\n{para}" if current else para

    if current:
        chunks.append(current.strip())

    return chunks


def _split_long_block(text: str, max_chars: int) -> list[str]:
    """Character-based splitting with overlap for oversized blocks."""
    pieces: list[str] = []
    start = 0
    while start < len(text):
        end = start + max_chars
        if end < len(text):
            break_at = text.rfind(" ", start, end)
            if break_at > start:
                end = break_at
        pieces.append(text[start:end].strip())
        start = end - OVERLAP_CHARS if end < len(text) else end
    return [p for p in pieces if p]


async def ingest_records(records: list[dict]) -> int:
    """Chunk, embed, and upsert records into ChromaDB. Returns total chunk count."""
    collection = get_collection()
    all_ids: list[str] = []
    all_docs: list[str] = []
    all_metas: list[dict] = []

    for record in records:
        chunks = chunk_text(record.get("content", ""))
        for idx, chunk in enumerate(chunks):
            chunk_id = f"{record['id']}_chunk_{idx}"
            all_ids.append(chunk_id)
            all_docs.append(chunk)
            all_metas.append({
                "source": record.get("source", ""),
                "course_code": record.get("course_code", ""),
                "title": record.get("title", ""),
                "license": record.get("license", ""),
                "url": record.get("url", ""),
                "chunk_index": idx,
                "resource_type": record.get("resource_type", ""),
                "subject": record.get("subject", ""),
                "term": record.get("term", ""),
                "institution": record.get("institution", ""),
                "has_accessibility_info": record.get("has_accessibility_info", False),
                "has_supplementary_materials": record.get("has_supplementary_materials", False),
            })

    if not all_docs:
        return 0

    BATCH_SIZE = 32
    all_embeddings: list[list[float]] = []
    for i in range(0, len(all_docs), BATCH_SIZE):
        batch = all_docs[i : i + BATCH_SIZE]
        batch_embeddings = await get_embeddings(batch)
        all_embeddings.extend(batch_embeddings)

    collection.upsert(
        ids=all_ids,
        documents=all_docs,
        embeddings=all_embeddings,
        metadatas=all_metas,
    )

    return len(all_ids)
