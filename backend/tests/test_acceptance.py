"""Acceptance tests: all 8 courses, cache-hit, LM-down, and no-result scenarios.

These tests mock the retrieval layer to validate the full pipeline
from route handler through evaluation and response construction.
"""

import time
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

COURSE_TEST_DATA = {
    "ARTS 1100": {
        "query": "art appreciation visual arts introduction",
        "title": "Intro to Art Appreciation",
        "content": "This textbook covers fundamental art concepts, visual culture, and art history from prehistoric to modern times.",
        "source": "Open ALG",
        "license": "CC BY 4.0",
        "resource_type": "textbook",
        "subject": "Art",
    },
    "ENGL 1101": {
        "query": "first-year composition writing",
        "title": "Writing First: Composition for College",
        "content": "A comprehensive guide to college composition, essay writing, rhetoric, and research methods.",
        "source": "Open ALG",
        "license": "CC BY-SA 4.0",
        "resource_type": "textbook",
        "subject": "English Composition",
    },
    "ENGL 1102": {
        "query": "literature and composition literary analysis",
        "title": "Literature and Composition Anthology",
        "content": "An anthology covering literary analysis, poetry, fiction, drama, and critical writing techniques.",
        "source": "Open ALG",
        "license": "CC BY 4.0",
        "resource_type": "textbook",
        "subject": "English Literature",
    },
    "HIST 2111": {
        "query": "US history to 1877 American history",
        "title": "American History to 1877",
        "content": "Survey of American history from colonization through Reconstruction era including political and social development.",
        "source": "Open ALG",
        "license": "CC BY 4.0",
        "resource_type": "textbook",
        "subject": "US History",
    },
    "HIST 2112": {
        "query": "US history since 1877 modern America",
        "title": "American History Since 1877",
        "content": "Modern American history covering industrialization, world wars, civil rights, and contemporary issues.",
        "source": "Open ALG",
        "license": "CC BY-SA 4.0",
        "resource_type": "textbook",
        "subject": "US History",
    },
    "ITEC 1001": {
        "query": "introduction to computer science information technology",
        "title": "Introduction to Information Technology",
        "content": "Fundamentals of computing, hardware, software, networking, and information systems for IT students.",
        "source": "GGC Syllabi",
        "license": "CC BY 4.0",
        "resource_type": "textbook",
        "subject": "Information Technology",
    },
    "BIOL 1101K": {
        "query": "biology molecules and cells",
        "title": "Biology: Molecules and Cells",
        "content": "Introductory biology covering molecular biology, cell structure, genetics, and biochemistry.",
        "source": "Open ALG",
        "license": "CC BY 4.0",
        "resource_type": "textbook",
        "subject": "Biology",
    },
    "BIOL 1102": {
        "query": "biology organisms ecosystems ecology",
        "title": "Biology: Organisms and Ecosystems",
        "content": "Biology covering ecology, evolution, organismal diversity, ecosystems, and environmental science.",
        "source": "Open ALG",
        "license": "CC BY-SA 4.0",
        "resource_type": "textbook",
        "subject": "Biology",
    },
}


def _make_hit(course_code: str, idx: int = 1) -> dict:
    data = COURSE_TEST_DATA[course_code]
    return {
        "id": f"oer-{course_code.lower().replace(' ', '')}-{idx:03d}_chunk_0",
        "content": data["content"],
        "title": data["title"],
        "source": data["source"],
        "course_code": course_code,
        "license": data["license"],
        "url": f"https://example.com/{course_code.lower().replace(' ', '-')}",
        "chunk_index": 0,
        "score": 0.82 + idx * 0.01,
        "metadata": {
            "resource_type": data["resource_type"],
            "subject": data["subject"],
            "term": "",
            "institution": "GGC",
            "has_accessibility_info": False,
            "has_supplementary_materials": True,
        },
    }


class TestAllCoursesAcceptance:
    """Each course gets a grounded search test validating full response structure."""

    @pytest.mark.parametrize("course_code", list(COURSE_TEST_DATA.keys()))
    def test_course_returns_valid_evaluated_response(self, course_code):
        data = COURSE_TEST_DATA[course_code]
        hits = [_make_hit(course_code, i) for i in range(1, 3)]

        with patch(
            "app.routes.search.search",
            new_callable=AsyncMock,
            return_value=hits,
        ):
            resp = client.post("/search", json={
                "query": data["query"],
                "course_code": course_code,
                "top_k": 5,
                "grounded": False,
            })

        assert resp.status_code == 200
        body = resp.json()
        assert EXPECTED_TOP_KEYS <= set(body.keys())
        assert len(body["results"]) >= 1

        for res in body["results"]:
            assert EXPECTED_RESOURCE_KEYS <= set(res.keys())
            assert res["title"], f"Missing title for {course_code}"
            assert res["description"], f"Missing description for {course_code}"
            assert res["source"], f"Missing source for {course_code}"
            assert res["license"]["details"], f"Missing license details for {course_code}"
            assert len(res["integration_tips"]) >= 1, f"Missing tips for {course_code}"
            assert isinstance(res["rubric_evaluation"], dict)

            rubric = res["rubric_evaluation"]
            assert "licensing_clarity" in rubric
            assert "accessibility_compliance" in rubric
            assert "modularity_and_adaptability" in rubric
            assert "supplementary_resources" in rubric

        internal_patterns = ["LLM", "fallback", "parse", "threshold"]
        for text in body.get("warnings", []) + body.get("errors", []):
            for pattern in internal_patterns:
                assert pattern.lower() not in text.lower()


class TestCacheHit:
    """Verify that repeated identical requests are served from cache."""

    def test_second_request_is_cached(self):
        hits = [_make_hit("BIOL 1101K")]
        payload = {
            "query": "biology molecules and cells",
            "course_code": "BIOL 1101K",
            "top_k": 5,
            "grounded": False,
        }

        with patch(
            "app.routes.search.search",
            new_callable=AsyncMock,
            return_value=hits,
        ) as mock_search:
            resp1 = client.post("/search", json=payload)
            assert resp1.status_code == 200
            body1 = resp1.json()

            resp2 = client.post("/search", json=payload)
            assert resp2.status_code == 200
            body2 = resp2.json()

        assert mock_search.call_count == 1
        assert body1["results"][0]["title"] == body2["results"][0]["title"]

    def test_cached_response_includes_debug_on_request(self):
        hits = [_make_hit("BIOL 1101K")]
        base_payload = {
            "query": "biology molecules cache debug test",
            "course_code": "BIOL 1101K",
            "top_k": 5,
            "grounded": False,
        }

        with patch(
            "app.routes.search.search",
            new_callable=AsyncMock,
            return_value=hits,
        ):
            client.post("/search", json=base_payload)
            resp = client.post("/search", json={**base_payload, "debug": True})

        assert resp.status_code == 200
        body = resp.json()
        assert body.get("_debug") is not None
        assert body["_debug"]["cache_hit"] is True


class TestLMStudioDown:
    """Verify graceful fallback when embedding service is unavailable."""

    def test_embedding_error_returns_structured_response(self):
        with patch(
            "app.routes.search.search",
            new_callable=AsyncMock,
            side_effect=EmbeddingError("connection refused"),
        ):
            resp = client.post("/search", json={
                "query": "biology molecules",
                "grounded": True,
            })

        assert resp.status_code == 200
        body = resp.json()
        assert EXPECTED_TOP_KEYS <= set(body.keys())
        assert body["results"] == []
        assert len(body["errors"]) > 0
        assert not any("LLM" in e for e in body["errors"])
        assert not any("Embedding" in e for e in body["errors"])


class TestNoResults:
    """Verify correct response when no results match."""

    def test_no_results_returns_empty_with_warning(self):
        with patch(
            "app.routes.search.search",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = client.post("/search", json={
                "query": "xyzzy12345 gibberish nonsense",
                "top_k": 5,
                "grounded": True,
            })

        assert resp.status_code == 200
        body = resp.json()
        assert body["results"] == []
        assert any("no matching" in w.lower() for w in body["warnings"])


class TestNonGroundedSearch:
    """Verify non-grounded search returns rule-based scores only."""

    def test_non_grounded_has_rule_based_rubric(self):
        hits = [_make_hit("ENGL 1101")]
        with patch(
            "app.routes.search.search",
            new_callable=AsyncMock,
            return_value=hits,
        ):
            resp = client.post("/search", json={
                "query": "first-year composition",
                "grounded": False,
                "debug": True,
            })

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["results"]) >= 1

        rubric = body["results"][0]["rubric_evaluation"]
        for llm_key in [
            "relevance_and_comprehensiveness",
            "interactivity_and_engagement",
            "pedagogical_soundness",
        ]:
            assert rubric[llm_key]["basis"] == "unavailable"

        debug = body.get("_debug", {})
        assert debug.get("evaluation_mode") == "rule_based"
