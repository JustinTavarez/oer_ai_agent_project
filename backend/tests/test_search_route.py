"""Integration tests for the /search endpoint (EvaluatedSearchResponse)."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.embeddings import EmbeddingError

client = TestClient(app)

EXPECTED_TOP_KEYS = {"query", "timestamp", "log_id", "summary", "results", "warnings", "errors"}
EXPECTED_RESOURCE_KEYS = {
    "resource_id", "title", "description", "source", "url", "course_code",
    "relevance", "license", "integration_tips", "rubric_evaluation",
}


def _valid_retrieval_hit(**overrides) -> dict:
    base = {
        "id": "oer-001_chunk_0",
        "content": "This is a test document about art appreciation and visual culture.",
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
        hits = [
            _valid_retrieval_hit(),
            _valid_retrieval_hit(id="oer-002_chunk_0", title="Art History"),
        ]

        with patch(
            "app.routes.search.search",
            new_callable=AsyncMock,
            return_value=hits,
        ):
            resp = client.post("/search", json={"query": "art resources"})

        assert resp.status_code == 200
        body = resp.json()
        assert EXPECTED_TOP_KEYS <= set(body.keys())
        assert len(body["results"]) >= 1
        for res in body["results"]:
            assert res["license"]["status"] == "open"
            assert isinstance(res["rubric_evaluation"], dict)
            assert res["description"]
            assert len(res["integration_tips"]) >= 1


class TestSearchPartialFailure:
    def test_search_partial_failure(self):
        good = _valid_retrieval_hit()
        bad = _valid_retrieval_hit(id="oer-bad_chunk_0", score=0.2)

        with patch(
            "app.routes.search.search",
            new_callable=AsyncMock,
            return_value=[good, bad],
        ):
            resp = client.post("/search", json={"query": "art resources"})

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["results"]) >= 1


class TestSearchAllMalformed:
    def test_search_empty_results(self):
        with patch(
            "app.routes.search.search",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = client.post("/search", json={"query": "art resources"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["results"] == []
        assert len(body["warnings"]) > 0


class TestSearchEmbeddingError:
    def test_search_embedding_error_returns_structured_response(self):
        with patch(
            "app.routes.search.search",
            new_callable=AsyncMock,
            side_effect=EmbeddingError("LM Studio down"),
        ):
            resp = client.post("/search", json={"query": "art resources"})

        assert resp.status_code == 200
        body = resp.json()
        assert EXPECTED_TOP_KEYS <= set(body.keys())
        assert body["results"] == []
        assert len(body["errors"]) > 0
        assert not any("LLM" in e for e in body["errors"])


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
        assert EXPECTED_TOP_KEYS <= set(body.keys())
        assert isinstance(body["results"], list)
        assert isinstance(body["warnings"], list)
        assert isinstance(body["errors"], list)
        assert body["log_id"]
        assert body["timestamp"]

        for res in body["results"]:
            assert EXPECTED_RESOURCE_KEYS <= set(res.keys())


class TestSearchDebugMode:
    def test_debug_flag_includes_debug_info(self):
        hits = [_valid_retrieval_hit()]
        with patch(
            "app.routes.search.search",
            new_callable=AsyncMock,
            return_value=hits,
        ):
            resp = client.post("/search", json={
                "query": "art resources",
                "debug": True,
            })

        assert resp.status_code == 200
        body = resp.json()
        assert "_debug" in body
        debug = body["_debug"]
        assert "evaluation_mode" in debug
        assert "cache_version" in debug

    def test_no_debug_flag_excludes_debug_info(self):
        hits = [_valid_retrieval_hit()]
        with patch(
            "app.routes.search.search",
            new_callable=AsyncMock,
            return_value=hits,
        ):
            resp = client.post("/search", json={"query": "art resources"})

        assert resp.status_code == 200
        body = resp.json()
        assert body.get("_debug") is None


class TestSearchResourceDefaults:
    """Verify every result has non-empty description, tips, and license details."""

    def test_fallback_resource_has_all_fields(self):
        hits = [_valid_retrieval_hit()]
        with patch(
            "app.routes.search.search",
            new_callable=AsyncMock,
            return_value=hits,
        ):
            resp = client.post("/search", json={
                "query": "art appreciation",
                "grounded": False,
            })

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["results"]) >= 1
        res = body["results"][0]
        assert res["description"]
        assert len(res["integration_tips"]) >= 1
        assert res["license"]["details"]


class TestSearchNoLeakedInternalText:
    """Ensure no implementation-detail text leaks to user-facing fields."""

    def test_no_internal_text_in_warnings_or_errors(self):
        hits = [_valid_retrieval_hit()]
        with patch(
            "app.routes.search.search",
            new_callable=AsyncMock,
            return_value=hits,
        ):
            resp = client.post("/search", json={"query": "art"})

        body = resp.json()
        internal_patterns = ["LLM", "fallback", "parse", "vector similarity"]
        for text in body.get("warnings", []) + body.get("errors", []):
            for pattern in internal_patterns:
                assert pattern.lower() not in text.lower(), (
                    f"Internal text '{pattern}' found in user-facing message: {text}"
                )
