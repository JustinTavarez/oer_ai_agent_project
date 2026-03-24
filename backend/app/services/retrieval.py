import logging
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple, Union

from app.services.chroma_client import get_collection
from app.services.embeddings import get_embedding

logger = logging.getLogger(__name__)

_SAFE_BOOL_TRUE = {True, 1, "true", "True", "TRUE"}
_SAFE_BOOL_FALSE = {False, 0, "false", "False", "FALSE"}
_SAFE_BOOL_ALL = _SAFE_BOOL_TRUE | _SAFE_BOOL_FALSE

_STRING_META_KEYS = (
    "title", "source", "course_code", "license", "url",
)
_STRING_NESTED_KEYS = (
    "resource_type", "subject", "term", "institution",
)
_BOOL_NESTED_KEYS = (
    "has_accessibility_info", "has_supplementary_materials",
)


def _coerce_bool(value: Any) -> Tuple[Optional[bool], bool]:
    """Return (coerced_value, ok).  ok is False when the value is not safe."""
    if value in _SAFE_BOOL_TRUE:
        return True, True
    if value in _SAFE_BOOL_FALSE:
        return False, True
    return None, False


def _coerce_chunk_index(value: Any) -> Tuple[Optional[int], bool]:
    """Return (coerced_value, ok).  Accepts int or whole-number float only."""
    if isinstance(value, int) and not isinstance(value, bool):
        return value, True
    if isinstance(value, float):
        if value == int(value):
            return int(value), True
        return None, False
    return None, False


def _normalize_hit(
    doc_id: Any,
    document: Any,
    metadata: Any,
    distance: Any,
) -> Tuple[Optional[Dict], Optional[str]]:
    """Validate and normalise a single raw ChromaDB hit.

    Returns (normalised_dict, None) on success, or (None, skip_reason) on
    failure.
    """
    if not isinstance(doc_id, str) or not doc_id:
        return None, "missing_id"

    if not isinstance(document, str) or not document:
        return None, "missing_document"

    if not isinstance(metadata, dict):
        return None, "invalid_metadata_type"

    if not isinstance(distance, (int, float)) or isinstance(distance, bool):
        return None, "invalid_distance"

    score = round(max(0.0, 1.0 - distance), 4)

    raw_ci = metadata.get("chunk_index", 0)
    chunk_index, ci_ok = _coerce_chunk_index(raw_ci)
    if not ci_ok:
        return None, "invalid_chunk_index"

    for key in _STRING_META_KEYS:
        val = metadata.get(key, "")
        if val is None or not isinstance(val, str):
            return None, "invalid_field_type"

    nested: Dict[str, Union[str, bool]] = {}
    for key in _STRING_NESTED_KEYS:
        val = metadata.get(key, "")
        if val is None or not isinstance(val, str):
            return None, "invalid_field_type"
        nested[key] = val

    for key in _BOOL_NESTED_KEYS:
        raw = metadata.get(key, False)
        coerced, ok = _coerce_bool(raw)
        if not ok:
            return None, "invalid_boolean_field"
        nested[key] = coerced

    return {
        "id": doc_id,
        "content": document,
        "title": metadata.get("title", ""),
        "source": metadata.get("source", ""),
        "course_code": metadata.get("course_code", ""),
        "license": metadata.get("license", ""),
        "url": metadata.get("url", ""),
        "chunk_index": chunk_index,
        "score": score,
        "metadata": nested,
    }, None


async def search(
    query: str,
    top_k: int = 5,
    course_code: Optional[str] = None,
    source: Optional[str] = None,
    license_filter: Optional[str] = None,
) -> List[Dict]:
    logger.info(
        "Retrieval started | query=%r top_k=%d course_code=%r source=%r",
        query, top_k, course_code, source,
    )

    query_embedding = await get_embedding(query)
    collection = get_collection()

    where_filter = _build_where_filter(course_code, source, license_filter)

    kwargs: dict = {
        "query_embeddings": [query_embedding],
        "n_results": top_k,
        "include": ["documents", "metadatas", "distances"],
    }
    if where_filter:
        kwargs["where"] = where_filter

    results = collection.query(**kwargs)

    ids = results.get("ids", [[]])[0]
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    raw_count = len(ids)
    logger.info(
        "ChromaDB returned %d raw hits (docs=%d, metas=%d, dists=%d)",
        raw_count, len(documents), len(metadatas), len(distances),
    )
    if metadatas:
        logger.debug("Sample raw metadata [0]: %r", metadatas[0])

    output: List[Dict] = []
    skip_reasons: Counter = Counter()

    for i in range(raw_count):
        doc_id = ids[i] if i < len(ids) else None
        document = documents[i] if i < len(documents) else None
        meta = metadatas[i] if i < len(metadatas) else None
        dist = distances[i] if i < len(distances) else None

        hit, reason = _normalize_hit(doc_id, document, meta, dist)
        if hit is not None:
            output.append(hit)
        else:
            skip_reasons[reason] += 1
            logger.warning(
                "Skipped hit %d | reason=%s id=%r", i, reason, doc_id,
            )

    skipped = sum(skip_reasons.values())
    logger.info(
        "Retrieval complete | raw=%d valid=%d skipped=%d reasons=%s",
        raw_count, len(output), skipped, dict(skip_reasons) or "none",
    )
    return output


def _build_where_filter(
    course_code: Optional[str],
    source: Optional[str],
    license_filter: Optional[str],
) -> Optional[Dict]:
    conditions: List[Dict] = []

    if course_code and course_code.lower() != "all":
        conditions.append({"course_code": {"$eq": course_code}})
    if source and source.lower() != "all":
        conditions.append({"source": {"$eq": source}})
    if license_filter and license_filter.lower() != "all":
        conditions.append({"license": {"$eq": license_filter}})

    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}
