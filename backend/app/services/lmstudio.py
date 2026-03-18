"""LM Studio chat-completion client for grounded OER responses."""

import json
from typing import Dict, List, Optional

import httpx

from app.config import settings

_client: Optional[httpx.AsyncClient] = None

GROUNDED_SYSTEM_PROMPT = """You are the OER AI Agent. You have been given a user query and a set of retrieved resource chunks from a database of Open Educational Resources.

Your job is to analyze the retrieved chunks and produce a structured JSON response. You MUST only reference information from the provided chunks. Do not invent resources.

Return a JSON object with these fields:
- "summary": A 2-3 sentence overview answering the user's query based on the retrieved resources.
- "recommendations": A JSON array where each element has:
  - "title": The resource title (from the chunk metadata)
  - "match_reason": One sentence explaining why this resource fits the query
  - "license": The license of the resource
  - "quality_summary": Brief assessment of quality and coverage based on the chunk content
  - "instructor_ideas": 1-2 practical ideas for how an instructor could use this resource
  - "source_link": The URL of the resource

Return ONLY the JSON object. No extra text before or after."""


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=60.0)
    return _client


async def close_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


async def generate_grounded_response(
    query: str,
    chunks: List[Dict],
) -> Dict:
    """Send query + retrieved chunks to the LLM for a grounded answer."""
    context_parts = []
    for i, chunk in enumerate(chunks):
        context_parts.append(
            f"--- Chunk {i + 1} ---\n"
            f"Title: {chunk.get('title', 'Unknown')}\n"
            f"Source: {chunk.get('source', 'Unknown')}\n"
            f"Course: {chunk.get('course_code', 'N/A')}\n"
            f"License: {chunk.get('license', 'Unknown')}\n"
            f"URL: {chunk.get('url', '')}\n"
            f"Content: {chunk.get('content', '')}\n"
        )

    user_content = (
        f"User query: {query}\n\n"
        f"Retrieved resource chunks:\n\n{''.join(context_parts)}"
    )

    messages = [
        {"role": "system", "content": GROUNDED_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    payload = {
        "model": settings.model_name,
        "messages": messages,
        "temperature": 0.3,
    }

    client = _get_client()
    resp = await client.post(settings.lm_studio_url, json=payload)
    resp.raise_for_status()
    result = resp.json()
    raw_text = result["choices"][0]["message"]["content"]

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        parsed = {"summary": raw_text, "recommendations": []}

    return {
        "summary": parsed.get("summary", ""),
        "recommendations": parsed.get("recommendations", []),
    }
