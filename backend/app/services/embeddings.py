import asyncio
from typing import List, Optional

import httpx

from app.config import settings


class EmbeddingError(Exception):
    """Raised when the embedding service is unreachable after retries."""


_client: Optional[httpx.AsyncClient] = None

MAX_RETRIES = 2
RETRY_BACKOFF_SECONDS = 1.0
REQUEST_TIMEOUT = 30.0


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT)
    return _client


async def close_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


async def get_embeddings(texts: List[str]) -> List[List[float]]:
    payload = {
        "model": settings.embedding_model,
        "input": texts,
    }
    url = f"{settings.lm_studio_base_url}/embeddings"
    client = _get_client()

    last_error: Optional[Exception] = None
    for attempt in range(1 + MAX_RETRIES):
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return [item["embedding"] for item in data["data"]]
        except (httpx.TimeoutException, httpx.HTTPStatusError) as exc:
            last_error = exc
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code < 500:
                break
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
        except httpx.ConnectError as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))

    raise EmbeddingError(
        f"Embedding request failed after {MAX_RETRIES + 1} attempts: {last_error}"
    )


async def get_embedding(text: str) -> List[float]:
    results = await get_embeddings([text])
    return results[0]
