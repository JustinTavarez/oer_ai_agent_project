import asyncio
import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_client: Optional[httpx.AsyncClient] = None

CHAT_TIMEOUT_S = 20.0
CHAT_MAX_RETRIES = 1
CHAT_RETRY_BACKOFF_S = 1.0

SYSTEM_PROMPT = """You are the OER AI Agent, an expert assistant that helps students and instructors discover high-quality Open Educational Resources (OER).

When the user asks about a topic, course, or learning goal, respond with a JSON array of OER recommendations. Each object in the array MUST have these fields:
- "title": Name of the resource
- "match_reason": One sentence explaining why it fits the request
- "license": The open license (e.g. "CC BY 4.0", "CC BY-SA 4.0", "Public Domain")
- "quality_summary": Brief assessment of quality and coverage
- "instructor_ideas": 1-2 practical ideas for how an instructor could use this resource
- "source_link": A URL to the resource (use a real URL if you know one, otherwise use a plausible placeholder)

Return ONLY the JSON array, no extra text before or after it. Return 2-4 recommendations per query.

If the user provides a course code, tailor recommendations to that course's subject area.
If the user provides a source preference (GGC Syllabi or Open ALG), prioritize resources from that source."""


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=CHAT_TIMEOUT_S)
    return _client


async def close_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


async def get_completion(
    prompt: str,
    course: Optional[str] = None,
    source_filter: Optional[str] = None,
) -> dict:
    user_content = prompt
    if course:
        user_content += f"\n\nCourse: {course}"
    if source_filter:
        user_content += f"\nPreferred source: {source_filter}"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    payload = {
        "model": settings.model_name,
        "messages": messages,
        "temperature": 0.7,
    }

    client = get_client()
    last_exc: Optional[Exception] = None
    for attempt in range(1 + CHAT_MAX_RETRIES):
        try:
            resp = await client.post(settings.lm_studio_url, json=payload)
            resp.raise_for_status()
            result = resp.json()
            return {"response": result["choices"][0]["message"]["content"]}
        except (httpx.TimeoutException, httpx.HTTPStatusError) as exc:
            last_exc = exc
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code < 500:
                break
            if attempt < CHAT_MAX_RETRIES:
                logger.warning("Chat LLM attempt %d failed (%s), retrying...", attempt + 1, exc)
                await asyncio.sleep(CHAT_RETRY_BACKOFF_S)
        except Exception as exc:
            last_exc = exc
            if attempt < CHAT_MAX_RETRIES:
                logger.warning("Chat LLM attempt %d failed (%s), retrying...", attempt + 1, exc)
                await asyncio.sleep(CHAT_RETRY_BACKOFF_S)

    logger.error("Chat LLM failed after %d attempt(s): %s", 1 + CHAT_MAX_RETRIES, last_exc)
    return {"response": "The AI model is currently slow to respond. Please try again in a moment."}


async def check_lm_studio() -> bool:
    """Ping LM Studio's models endpoint to verify connectivity."""
    try:
        base = settings.lm_studio_url.rsplit("/v1/", 1)[0]
        client = get_client()
        resp = await client.get(f"{base}/v1/models", timeout=5.0)
        return resp.status_code == 200
    except Exception:
        return False
