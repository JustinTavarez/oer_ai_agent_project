"""Integration tests for the /search endpoint."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.embeddings import EmbeddingError

client = TestClient(app)


def _valid_retrieval_hit(**overrides) -> dict:
    base = {
        "id": "oer-001_chunk_0",
        "content": "This is a test document about art.",
        "title": "Intro to Art",
        "source": "Open ALG",
        "course_code": "ARTS 1100",
        "license": "CC BY 4.0",
        "url": "https://example.com",
        "chunk_index": 0,
        "score": 0.85,
        "metadata": {
            "resource_type": "textbook",
            "subject": "Art",
            "term": "",
            "institution": "",
            "has_accessibility_info": False,
            "has_supplementary_materials": True,
        },
    }
    base.update(overrides)
    return base


class TestSearchValidResults:
    def test_search_valid_results(self):
        hits = [_valid_retrieval_hit(), _valid_retrieval_hit(id="oer-002_chunk_0")]

        with patch(
            "app.routes.search.search",
            new_callable=AsyncMock,
            return_value=hits,
        ):
            resp = client.post("/search", json={"query": "art resources"})

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["results"]) == 2
        assert body["results"][0]["id"] == "oer-001_chunk_0"
        assert body["grounded_response"] is None
        assert isinstance(body["message"], str)


class TestSearchPartialFailure:
    def test_search_partial_failure(self):
        good = _valid_retrieval_hit()
        bad = _valid_retrieval_hit(id="bad", score="not_a_float")

        with patch(
            "app.routes.search.search",
            new_callable=AsyncMock,
            return_value=[good, bad],
        ):
            resp = client.post("/search", json={"query": "art resources"})

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["results"]) >= 1
        assert body["results"][0]["id"] == "oer-001_chunk_0"


class TestSearchAllMalformed:
    def test_search_all_malformed(self):
        with patch(
            "app.routes.search.search",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = client.post("/search", json={"query": "art resources"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["results"] == []
        assert body["message"] != ""


class TestSearchEmbeddingError:
    def test_search_embedding_error(self):
        with patch(
            "app.routes.search.search",
            new_callable=AsyncMock,
            side_effect=EmbeddingError("LM Studio down"),
        ):
            resp = client.post("/search", json={"query": "art resources"})

        assert resp.status_code == 503
        assert "Embedding service unavailable" in resp.json()["detail"]


class TestSearchResponseShapeStable:
    @pytest.mark.parametrize(
        "return_value",
        [
            [_valid_retrieval_hit()],
            [],
        ],
        ids=["with_results", "empty_results"],
    )
    def test_search_response_shape_stable(self, return_value):
        with patch(
            "app.routes.search.search",
            new_callable=AsyncMock,
            return_value=return_value,
        ):
            resp = client.post("/search", json={"query": "test"})

        assert resp.status_code == 200
        body = resp.json()
        assert "results" in body
        assert "grounded_response" in body
        assert "message" in body
        assert isinstance(body["results"], list)
