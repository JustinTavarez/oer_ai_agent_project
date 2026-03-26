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
MAX_CONTEXT_RESOURCES = 5

EVALUATED_SYSTEM_PROMPT = """\
You are the OER AI Agent. You receive a user query and a curated set of Open Educational Resources with metadata. Analyze ONLY the provided resources. Do NOT invent resources, licenses, or URLs.

You MUST return a single valid JSON object. The "summary" field is REQUIRED and must not be empty.

{
  "summary": "REQUIRED. 2-3 sentences summarizing the best resources found for the user's query. Always include this field with a meaningful answer.",
  "recommendations": [
    {
      "resource_id": "the resource_id from the input",
      "title": "exact title from the input",
      "description": "1-2 sentence description of the resource content and purpose",
      "relevance": {
        "score": 0.0 to 1.0,
        "reasoning": "why this resource matches the query"
      },
      "license": {
        "status": "open" or "unclear" or "not_open" or "unknown",
        "details": "license name and what it permits"
      },
      "integration_tips": ["1-2 practical ideas for how an instructor could use this resource"],
      "rubric_evaluation": {
        "relevance_and_comprehensiveness": {"score": 1-5, "reasoning": "..."},
        "interactivity_and_engagement": {"score": 1-5, "reasoning": "..."},
        "pedagogical_soundness": {"score": 1-5, "reasoning": "..."}
      },
      "warnings": ["any caveats, or empty array"]
    }
  ]
}

Rules:
- The "summary" field is REQUIRED. Always write 2-3 sentences about what was found.
- Only use "open" for license status if the license is a recognized Creative Commons or public domain license.
- Use "unclear" if the license text is ambiguous or non-standard.
- Use "unknown" if no license information is provided.
- Do not invent licenses. If the license field says "CC BY 4.0", report it as open. Do not guess beyond what is given.
- Do not fabricate certainty. If evidence is limited, say so in the reasoning.
- Mark uncertain evaluations explicitly in the reasoning text.
- Scores are 1-5 integers. 1=poor, 3=adequate, 5=excellent.
- Return ONLY the JSON object. No markdown fences, no extra text before or after."""


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


def _extract_resource_id(chunk_id: str) -> str:
    """Extract parent resource ID from a chunk ID like 'oer-001_chunk_0'."""
    parts = chunk_id.split("_chunk_")
    return parts[0] if len(parts) >= 2 else chunk_id


def build_context_pack(raw_results: List[Dict]) -> List[Dict]:
    """Deduplicate, filter, and clean raw retrieval hits into a context pack.

    1. Group chunks by resource ID (split on '_chunk_').
    2. Per resource: keep best-scoring chunk, merge metadata.
    3. Filter resources whose best score is below MIN_SCORE_THRESHOLD.
    4. Sort by best score descending, take top MAX_CONTEXT_RESOURCES.
    5. Return clean dicts with verified metadata fields.
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
            "content": best.get("content", ""),
            "score": best_score,
        })

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


def _try_parse_json(raw_text: str) -> Optional[Dict]:
    """Attempt to parse JSON from LLM output, including markdown-fenced."""
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
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return None


async def generate_evaluated_response(
    query: str,
    raw_results: List[Dict],
) -> Dict[str, Any]:
    """Build context pack, call LLM, validate response. Returns parsed dict
    with keys: summary, recommendations, llm_success, llm_duration_ms,
    parse_failures, fallback_used, warnings.
    """
    context_pack = build_context_pack(raw_results)

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

    user_content = _build_user_message(query, context_pack)
    messages = [
        {"role": "system", "content": EVALUATED_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
    payload = {
        "model": settings.model_name,
        "messages": messages,
        "temperature": 0.3,
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
        logger.warning("LLM returned unparseable JSON. Raw text: %.500s", raw_text)
        result["warnings"].append("LLM returned invalid JSON; showing raw retrieval results.")
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

    return result


async def generate_grounded_response(
    query: str, chunks: List[Dict]
) -> Dict:
    """Backward-compatible alias."""
    resp = await generate_evaluated_response(query, chunks)
    return {"summary": resp["summary"], "recommendations": resp["recommendations"]}
