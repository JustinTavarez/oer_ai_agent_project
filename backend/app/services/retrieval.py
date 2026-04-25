import asyncio
import logging
import re
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
# Optional string keys we forward but tolerate when missing/None
# (older sample data may not have them).
_OPTIONAL_STRING_NESTED_KEYS = ("content_kind",)

# Course codes follow Banner conventions: 3-4 uppercase letters, a space,
# then 4 digits with an optional trailing letter (e.g. BIOL 1101K).
_COURSE_CODE_RE = re.compile(r"\b([A-Z]{3,4})\s*(\d{4}[A-Z]?)\b", re.IGNORECASE)

# Boost applied to the similarity score (0.0-1.0) of any retrieval hit
# whose course_code matches the code detected in the query text. Tuned to
# move a 0.55 same-course hit ahead of a 0.65 wrong-course hit without
# steamrolling clearly-better cross-course matches.
COURSE_CODE_QUERY_BOOST = 0.20

# When the user asks about a specific course we over-fetch from Chroma so
# the same-course re-rank has enough material to work with even when the
# raw embeddings rank a wrong-course hit slightly higher.
_OVERFETCH_FACTOR = 4
_OVERFETCH_FLOOR = 20


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

    for key in _OPTIONAL_STRING_NESTED_KEYS:
        val = metadata.get(key, "")
        if val is None:
            val = ""
        if not isinstance(val, str):
            val = str(val)
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


def extract_course_code_from_query(query: str) -> Optional[str]:
    """Detect a course code in a free-text query (e.g. 'HIST 2112').

    Returns the canonical "PREFIX NUMBER" form (e.g. 'BIOL 1101K') or None
    if the query does not look like it mentions a specific course.
    """
    if not query:
        return None
    m = _COURSE_CODE_RE.search(query)
    if not m:
        return None
    prefix = m.group(1).upper()
    number = m.group(2).upper()
    return f"{prefix} {number}"


async def search(
    query: str,
    top_k: int = 5,
    course_code: Optional[str] = None,
    source: Optional[str] = None,
    license_filter: Optional[str] = None,
) -> List[Dict]:
    # Detect course code in the query text only when the caller has not
    # explicitly filtered by course. The detected code is used as a soft
    # re-rank hint, never as a hard Chroma filter, so subject-mapped
    # Open ALG resources can still surface for the related topic.
    detected_code: Optional[str] = None
    if not course_code:
        detected_code = extract_course_code_from_query(query)

    logger.info(
        "Retrieval started | query=%r top_k=%d course_code=%r source=%r detected_code=%r",
        query, top_k, course_code, source, detected_code,
    )

    query_embedding = await get_embedding(query)
    collection = get_collection()

    where_filter = _build_where_filter(course_code, source, license_filter)

    # When we have any course-code signal (explicit or detected) we
    # over-fetch from Chroma so the post-Chroma re-rank has enough
    # candidates to promote same-course hits without losing variety.
    n_results = top_k
    if course_code or detected_code:
        n_results = max(top_k * _OVERFETCH_FACTOR, _OVERFETCH_FLOOR)

    kwargs: dict = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if where_filter:
        kwargs["where"] = where_filter

    results = await asyncio.to_thread(collection.query, **kwargs)

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

    # Soft course-code boost: bump same-course hits before the LLM/rule
    # layer sees them. Boost is recorded on a separate key so anything
    # downstream that needs the raw similarity (e.g. analytics) can still
    # find it under `raw_score`.
    boost_target = (course_code or detected_code or "").strip().upper()
    boosted = 0
    fallback_added = 0
    if boost_target:
        for hit in output:
            hit["raw_score"] = hit.get("score", 0.0)
            if (hit.get("course_code") or "").strip().upper() == boost_target:
                hit["score"] = min(1.0, hit["raw_score"] + COURSE_CODE_QUERY_BOOST)
                hit["course_match"] = True
                boosted += 1
            else:
                hit["course_match"] = False

        # Course-code fallback: only meaningful when the user did NOT
        # already pass an explicit course_code filter (in that case
        # Chroma already filtered by that course, so a second filtered
        # call would just return the same empty set). Triggered when the
        # bare-text query embedding fails to surface the detected course
        # (e.g. "ITEC 1001" against a single curated-resources page).
        if boosted == 0 and not course_code:
            fallback_hits = await _course_code_fallback(
                query_embedding, boost_target, source, license_filter, top_k,
            )
            for hit in fallback_hits:
                hit["raw_score"] = hit.get("score", 0.0)
                hit["score"] = min(1.0, hit["raw_score"] + COURSE_CODE_QUERY_BOOST)
                hit["course_match"] = True
                output.append(hit)
                fallback_added += 1
                boosted += 1

        # Re-sort by boosted score so callers that just take the head get
        # the re-ranked order. Then trim to the originally requested top_k.
        output.sort(key=lambda h: h.get("score", 0.0), reverse=True)
        output = output[:top_k]

    skipped = sum(skip_reasons.values())
    logger.info(
        "Retrieval complete | raw=%d valid=%d kept=%d boosted=%d fallback=%d skipped=%d reasons=%s",
        raw_count, len(output) + skipped - boosted, len(output), boosted,
        fallback_added, skipped, dict(skip_reasons) or "none",
    )
    return output


async def _course_code_fallback(
    query_embedding: List[float],
    course_code_upper: str,
    source: Optional[str],
    license_filter: Optional[str],
    top_k: int,
) -> List[Dict]:
    """Fetch the best chunks for a course_code with a hard Chroma filter.

    Used only when the primary over-fetch did not surface any same-course
    hits, so the search still returns the canonical resource for tiny
    courses (e.g. a single Open ALG project) instead of returning all
    cross-course neighbours.
    """
    where_filter = _build_where_filter(course_code_upper, source, license_filter)
    if not where_filter:
        # _build_where_filter only emits a non-None value when course_code
        # passes its 'all' check; build it directly for safety.
        where_filter = {"course_code": {"$eq": course_code_upper}}

    collection = get_collection()
    kwargs: dict = {
        "query_embeddings": [query_embedding],
        "n_results": max(top_k, 3),
        "include": ["documents", "metadatas", "distances"],
        "where": where_filter,
    }
    try:
        results = await asyncio.to_thread(collection.query, **kwargs)
    except Exception as exc:  # noqa: BLE001
        logger.warning("course-code fallback query failed: %s", exc)
        return []

    ids = results.get("ids", [[]])[0]
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    out: List[Dict] = []
    for i in range(len(ids)):
        doc_id = ids[i] if i < len(ids) else None
        document = documents[i] if i < len(documents) else None
        meta = metadatas[i] if i < len(metadatas) else None
        dist = distances[i] if i < len(distances) else None
        hit, _ = _normalize_hit(doc_id, document, meta, dist)
        if hit is not None:
            out.append(hit)
    return out


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
