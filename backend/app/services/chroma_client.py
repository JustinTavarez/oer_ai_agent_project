from typing import Optional

import chromadb

from app.config import settings

_client: Optional[chromadb.ClientAPI] = None


def get_chroma_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=settings.chroma_path)
    return _client


def _get_named_collection(name: str) -> chromadb.Collection:
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


def get_collection() -> chromadb.Collection:
    """Return the collection currently marked active in config.

    Flip between sample and real data by setting the
    CHROMA_ACTIVE_COLLECTION env var; no code changes required.
    """
    return _get_named_collection(settings.chroma_active_collection)


def get_sample_collection() -> chromadb.Collection:
    """Always return the sample-data collection, regardless of the active setting."""
    return _get_named_collection(settings.chroma_sample_collection)


def get_real_collection() -> chromadb.Collection:
    """Always return the real-data collection, regardless of the active setting.

    Used by the real-data seed/verify/validate scripts so they never
    accidentally touch the sample collection.
    """
    return _get_named_collection(settings.chroma_real_collection)
