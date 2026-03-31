"""LM Studio chat-completion client for evaluated OER responses."""

import json
import logging
import re
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_client: Optional[httpx.AsyncClient] = None

MIN_SCORE_THRESHOLD = 0.4
MAX_CONTEXT_RESOURCES = 2
COURSE_BOOST = 0.10

_response_cache: Dict[tuple, tuple] = {}
CACHE_TTL_S = 600
CACHE_MAX = 64

EVALUATED_SYSTEM_PROMPT = """\
Respond with a single JSON object. No markdown, no code fences, no text outside the JSON.

{"summary":"2-3 short sentences on best resources found (never empty)",
 "recommendations":[{"resource_id":"from input","title":"from input",
   "description":"1 sentence",
   "relevance":{"score":0.0-1.0,"reasoning":"brief"},
   "license":{"status":"open|unclear|not_open|unknown","details":"short"},
   "rubric_evaluation":{
     "relevance_and_comprehensiveness":{"score":1-5,"reasoning":"one sentence"},
     "interactivity_and_engagement":{"score":1-5,"reasoning":"one sentence"},
     "pedagogical_soundness":{"score":1-5,"reasoning":"one sentence"}}}]}

Analyze ONLY provided resources. Do not invent data. "open" only for CC/public domain. Scores 1-5 integers. Output raw JSON only."""


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=90.0)
    return _client


async def close_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


def _make_cache_key(query: str, resource_ids: List[str]) -> tuple:
    return (query.strip().lower(), tuple(sorted(resource_ids)))


def _cache_get(key: tuple) -> Optional[Dict[str, Any]]:
    entry = _response_cache.get(key)
    if entry is None:
        return None
    result, expiry = entry
    if time.monotonic() > expiry:
        _response_cache.pop(key, None)
        return None
    return result


def _cache_put(key: tuple, result: Dict[str, Any]) -> None:
    if len(_response_cache) >= CACHE_MAX:
        now = time.monotonic()
        expired = [k for k, (_, exp) in _response_cache.items() if now > exp]
        for k in expired:
            _response_cache.pop(k, None)
        if len(_response_cache) >= CACHE_MAX:
            _response_cache.pop(next(iter(_response_cache)), None)
    _response_cache[key] = (result, time.monotonic() + CACHE_TTL_S)


def _extract_resource_id(chunk_id: str) -> str:
    """Extract parent resource ID from a chunk ID like 'oer-001_chunk_0'."""
    parts = chunk_id.split("_chunk_")
    return parts[0] if len(parts) >= 2 else chunk_id


def build_context_pack(
    raw_results: List[Dict],
    course_code: Optional[str] = None,
) -> List[Dict]:
    """Deduplicate, filter, and clean raw retrieval hits into a context pack.

    1. Group chunks by resource ID (split on '_chunk_').
    2. Per resource: keep best-scoring chunk, merge metadata.
    3. Filter resources whose best score is below MIN_SCORE_THRESHOLD.
    4. Boost same-course resources when course_code is provided.
    5. Suppress cross-course neighbors when enough same-course results exist.
    6. Sort by best score descending, take top MAX_CONTEXT_RESOURCES.
    7. Return clean dicts with verified metadata fields.
    """
    groups: Dict[str, List[Dict]] = defaultdict(list)
    for hit in raw_results:
        resource_id = _extract_resource_id(hit.get("id", ""))
        groups[resource_id].append(hit)

    resources: List[Dict] = []
    for resource_id, chunks in groups.items():
        best = max(chunks, key=lambda c: c.get("score", 0.0))
        best_score = best.get("score", 0.0)

        if best_score < MIN_SCORE_THRESHOLD:
            continue

        meta = best.get("metadata", {})
        resources.append({
            "resource_id": resource_id,
            "title": best.get("title", ""),
            "source": best.get("source", ""),
            "course_code": best.get("course_code", ""),
            "license": best.get("license", ""),
            "url": best.get("url", ""),
            "resource_type": meta.get("resource_type", ""),
            "subject": meta.get("subject", ""),
            "has_accessibility_info": meta.get("has_accessibility_info", False),
            "has_supplementary_materials": meta.get("has_supplementary_materials", False),
            "content": best.get("content", "")[:500],
            "score": best_score,
        })

    if course_code:
        cc_upper = course_code.strip().upper()
        for r in resources:
            if r["course_code"].strip().upper() == cc_upper:
                r["score"] = min(1.0, r["score"] + COURSE_BOOST)

        same = [r for r in resources if r["course_code"].strip().upper() == cc_upper]
        if len(same) >= 2:
            min_same = min(r["score"] for r in same)
            resources = [
                r for r in resources
                if r["course_code"].strip().upper() == cc_upper or r["score"] >= min_same
            ]

    resources.sort(key=lambda r: r["score"], reverse=True)
    return resources[:MAX_CONTEXT_RESOURCES]


def _build_user_message(query: str, context_pack: List[Dict]) -> str:
    """Format the user message from query + cleaned context pack."""
    parts = [f"User query: {query}\n"]
    for i, res in enumerate(context_pack):
        parts.append(
            f"\n--- Resource {i + 1} ---\n"
            f"resource_id: {res['resource_id']}\n"
            f"Title: {res['title']}\n"
            f"Source: {res['source']}\n"
            f"Course code: {res['course_code']}\n"
            f"License: {res['license']}\n"
            f"URL: {res['url']}\n"
            f"Resource type: {res['resource_type']}\n"
            f"Subject: {res['subject']}\n"
            f"Content:\n{res['content']}\n"
        )
    return "".join(parts)


def _repair_json(text: str) -> Optional[Dict]:
    """Conservative repair: trailing commas and minimal brace closure only."""
    fixed = re.sub(r",\s*([}\]])", r"\1", text)

    open_braces = fixed.count("{") - fixed.count("}")
    open_brackets = fixed.count("[") - fixed.count("]")
    if 0 < open_braces <= 2 and open_brackets >= 0:
        fixed += "]" * open_brackets + "}" * open_braces
    elif open_braces < 0 or open_brackets < 0:
        return None

    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        return None


def _try_parse_json(raw_text: str) -> Optional[Dict]:
    """Attempt to parse JSON from LLM output with conservative repair."""
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        extracted = match.group()
        try:
            return json.loads(extracted)
        except json.JSONDecodeError:
            pass
        repaired = _repair_json(extracted)
        if repaired is not None:
            return repaired

    return None


async def generate_evaluated_response(
    query: str,
    raw_results: List[Dict],
    course_code: Optional[str] = None,
) -> Dict[str, Any]:
    """Build context pack, call LLM, validate response. Returns parsed dict
    with keys: summary, recommendations, llm_success, llm_duration_ms,
    parse_failures, fallback_used, warnings.
    """
    context_pack = build_context_pack(raw_results, course_code=course_code)

    result: Dict[str, Any] = {
        "summary": "",
        "recommendations": [],
        "context_pack": context_pack,
        "llm_success": False,
        "llm_duration_ms": 0,
        "parse_failures": 0,
        "fallback_used": False,
        "warnings": [],
    }

    if not context_pack:
        result["summary"] = "No resources met the relevance threshold for this query."
        result["warnings"].append("All retrieval results scored below the minimum threshold.")
        result["fallback_used"] = True
        return result

    cache_key = _make_cache_key(query, [r["resource_id"] for r in context_pack])
    cached = _cache_get(cache_key)
    if cached is not None:
        logger.info("Cache hit for query=%r", query)
        cached["context_pack"] = context_pack
        return cached

    user_content = _build_user_message(query, context_pack)
    messages = [
        {"role": "system", "content": EVALUATED_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
    payload = {
        "model": settings.model_name,
        "messages": messages,
        "temperature": 0.1,
    }

    start = time.monotonic()
    try:
        client = _get_client()
        resp = await client.post(settings.lm_studio_url, json=payload)
        resp.raise_for_status()
        llm_result = resp.json()
        raw_text = llm_result["choices"][0]["message"]["content"]
        result["llm_duration_ms"] = int((time.monotonic() - start) * 1000)
    except Exception as exc:
        result["llm_duration_ms"] = int((time.monotonic() - start) * 1000)
        logger.error("LM Studio request failed: %s", exc)
        result["warnings"].append(f"LLM evaluation unavailable: {exc}")
        result["fallback_used"] = True
        return result

    parsed = _try_parse_json(raw_text)
    if parsed is None:
        result["parse_failures"] = 1
        logger.warning("LLM returned unparseable JSON. Raw text:\n%.2000s", raw_text)
        result["warnings"].append("Results shown are based on search relevance.")
        result["fallback_used"] = True
        return result

    result["llm_success"] = True
    result["summary"] = parsed.get("summary", "")
    result["recommendations"] = parsed.get("recommendations", [])

    if not isinstance(result["recommendations"], list):
        result["recommendations"] = []
        result["parse_failures"] += 1
        logger.warning("LLM 'recommendations' was not a list.")
        result["warnings"].append("LLM response had malformed recommendations.")

    if not result["summary"] or not result["summary"].strip():
        titles = [r["title"] for r in context_pack if r.get("title")]
        result["summary"] = (
            f"Here are {len(context_pack)} open educational resource(s) matching your query: "
            + ", ".join(titles)
            + "."
        )
        result["warnings"].append("Summary was generated from search results.")

    _cache_put(cache_key, result)
    return result


async def generate_grounded_response(
    query: str, chunks: List[Dict], course_code: Optional[str] = None,
) -> Dict:
    """Backward-compatible alias."""
    resp = await generate_evaluated_response(query, chunks, course_code=course_code)
    return {"summary": resp["summary"], "recommendations": resp["recommendations"]}
