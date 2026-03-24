"""Unit tests for retrieval normalisation and the search() pipeline."""

from collections import Counter
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.retrieval import _coerce_bool, _coerce_chunk_index, _normalize_hit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_meta() -> dict:
    return {
        "title": "Intro to Art",
        "source": "Open ALG",
        "course_code": "ARTS 1100",
        "license": "CC BY 4.0",
        "url": "https://example.com",
        "chunk_index": 0,
        "resource_type": "textbook",
        "subject": "Art",
        "term": "",
        "institution": "",
        "has_accessibility_info": False,
        "has_supplementary_materials": True,
    }


def _make_chroma_results(ids, documents, metadatas, distances):
    return {
        "ids": [ids],
        "documents": [documents],
        "metadatas": [metadatas],
        "distances": [distances],
    }


# ===================================================================
# _normalize_hit — happy path
# ===================================================================

class TestNormalizeHitValid:
    def test_valid_hit_passes_through(self):
        hit, reason = _normalize_hit("id-1", "Some content", _valid_meta(), 0.25)
        assert reason is None
        assert hit is not None
        assert hit["id"] == "id-1"
        assert hit["content"] == "Some content"
        assert hit["score"] == 0.75
        assert hit["chunk_index"] == 0
        assert hit["metadata"]["has_supplementary_materials"] is True


# ===================================================================
# _normalize_hit — skip reasons
# ===================================================================

class TestNormalizeHitSkips:
    def test_metadata_is_none(self):
        hit, reason = _normalize_hit("id-1", "text", None, 0.1)
        assert hit is None
        assert reason == "invalid_metadata_type"

    def test_metadata_is_not_dict_string(self):
        hit, reason = _normalize_hit("id-1", "text", "bad", 0.1)
        assert hit is None
        assert reason == "invalid_metadata_type"

    def test_metadata_is_not_dict_list(self):
        hit, reason = _normalize_hit("id-1", "text", ["bad"], 0.1)
        assert hit is None
        assert reason == "invalid_metadata_type"

    def test_distance_is_none(self):
        hit, reason = _normalize_hit("id-1", "text", _valid_meta(), None)
        assert hit is None
        assert reason == "invalid_distance"

    def test_distance_is_string(self):
        hit, reason = _normalize_hit("id-1", "text", _valid_meta(), "0.5")
        assert hit is None
        assert reason == "invalid_distance"

    def test_distance_is_bool(self):
        hit, reason = _normalize_hit("id-1", "text", _valid_meta(), True)
        assert hit is None
        assert reason == "invalid_distance"

    def test_document_is_none(self):
        hit, reason = _normalize_hit("id-1", None, _valid_meta(), 0.1)
        assert hit is None
        assert reason == "missing_document"

    def test_document_is_empty(self):
        hit, reason = _normalize_hit("id-1", "", _valid_meta(), 0.1)
        assert hit is None
        assert reason == "missing_document"

    def test_id_is_none(self):
        hit, reason = _normalize_hit(None, "text", _valid_meta(), 0.1)
        assert hit is None
        assert reason == "missing_id"

    def test_id_is_empty_string(self):
        hit, reason = _normalize_hit("", "text", _valid_meta(), 0.1)
        assert hit is None
        assert reason == "missing_id"

    def test_id_is_not_string(self):
        hit, reason = _normalize_hit(123, "text", _valid_meta(), 0.1)
        assert hit is None
        assert reason == "missing_id"

    def test_string_field_is_none(self):
        meta = _valid_meta()
        meta["title"] = None
        hit, reason = _normalize_hit("id-1", "text", meta, 0.1)
        assert hit is None
        assert reason == "invalid_field_type"

    def test_nested_string_field_is_none(self):
        meta = _valid_meta()
        meta["subject"] = None
        hit, reason = _normalize_hit("id-1", "text", meta, 0.1)
        assert hit is None
        assert reason == "invalid_field_type"


# ===================================================================
# chunk_index coercion
# ===================================================================

class TestChunkIndex:
    def test_chunk_index_float_whole_number(self):
        meta = _valid_meta()
        meta["chunk_index"] = 3.0
        hit, reason = _normalize_hit("id-1", "text", meta, 0.1)
        assert reason is None
        assert hit["chunk_index"] == 3
        assert isinstance(hit["chunk_index"], int)

    def test_chunk_index_float_fractional(self):
        meta = _valid_meta()
        meta["chunk_index"] = 3.7
        hit, reason = _normalize_hit("id-1", "text", meta, 0.1)
        assert hit is None
        assert reason == "invalid_chunk_index"

    def test_chunk_index_string(self):
        meta = _valid_meta()
        meta["chunk_index"] = "3"
        hit, reason = _normalize_hit("id-1", "text", meta, 0.1)
        assert hit is None
        assert reason == "invalid_chunk_index"

    def test_chunk_index_missing_defaults_to_zero(self):
        meta = _valid_meta()
        del meta["chunk_index"]
        hit, reason = _normalize_hit("id-1", "text", meta, 0.1)
        assert reason is None
        assert hit["chunk_index"] == 0


# ===================================================================
# Boolean coercion
# ===================================================================

class TestBooleanCoercion:
    def test_bool_true_passthrough(self):
        assert _coerce_bool(True) == (True, True)

    def test_bool_false_passthrough(self):
        assert _coerce_bool(False) == (False, True)

    def test_int_1(self):
        assert _coerce_bool(1) == (True, True)

    def test_int_0(self):
        assert _coerce_bool(0) == (False, True)

    def test_string_true_lower(self):
        assert _coerce_bool("true") == (True, True)

    def test_string_false_upper(self):
        assert _coerce_bool("FALSE") == (False, True)

    def test_string_True_title(self):
        assert _coerce_bool("True") == (True, True)

    def test_rejects_int_2(self):
        assert _coerce_bool(2) == (None, False)

    def test_rejects_string_yes(self):
        assert _coerce_bool("yes") == (None, False)

    def test_rejects_none(self):
        assert _coerce_bool(None) == (None, False)

    def test_rejects_string_1(self):
        assert _coerce_bool("1") == (None, False)

    def test_boolean_field_rejects_unsafe_in_hit(self):
        meta = _valid_meta()
        meta["has_accessibility_info"] = 2
        hit, reason = _normalize_hit("id-1", "text", meta, 0.1)
        assert hit is None
        assert reason == "invalid_boolean_field"

    def test_boolean_field_rejects_yes_in_hit(self):
        meta = _valid_meta()
        meta["has_supplementary_materials"] = "yes"
        hit, reason = _normalize_hit("id-1", "text", meta, 0.1)
        assert hit is None
        assert reason == "invalid_boolean_field"

    def test_boolean_field_rejects_none_in_hit(self):
        meta = _valid_meta()
        meta["has_accessibility_info"] = None
        hit, reason = _normalize_hit("id-1", "text", meta, 0.1)
        assert hit is None
        assert reason == "invalid_boolean_field"


# ===================================================================
# Score clamping
# ===================================================================

class TestScoreClamping:
    def test_normal_distance(self):
        hit, _ = _normalize_hit("id-1", "text", _valid_meta(), 0.3)
        assert hit["score"] == 0.7

    def test_zero_distance(self):
        hit, _ = _normalize_hit("id-1", "text", _valid_meta(), 0.0)
        assert hit["score"] == 1.0

    def test_distance_one(self):
        hit, _ = _normalize_hit("id-1", "text", _valid_meta(), 1.0)
        assert hit["score"] == 0.0

    def test_large_distance_clamped(self):
        hit, _ = _normalize_hit("id-1", "text", _valid_meta(), 1.5)
        assert hit["score"] == 0.0

    def test_distance_two_clamped(self):
        hit, _ = _normalize_hit("id-1", "text", _valid_meta(), 2.0)
        assert hit["score"] == 0.0


# ===================================================================
# search() integration — mocked ChromaDB
# ===================================================================

class TestSearchIntegration:
    @pytest.mark.asyncio
    async def test_one_bad_result_among_valid(self):
        good_meta = _valid_meta()
        results = _make_chroma_results(
            ids=["a", "b", "c"],
            documents=["doc a", "doc b", "doc c"],
            metadatas=[good_meta, None, good_meta],
            distances=[0.1, 0.2, 0.3],
        )

        mock_collection = MagicMock()
        mock_collection.query.return_value = results

        with patch("app.services.retrieval.get_embedding", new_callable=AsyncMock, return_value=[0.1] * 384), \
             patch("app.services.retrieval.get_collection", return_value=mock_collection):
            from app.services.retrieval import search as do_search
            output = await do_search("test query", top_k=3)

        assert len(output) == 2
        assert output[0]["id"] == "a"
        assert output[1]["id"] == "c"

    @pytest.mark.asyncio
    async def test_all_results_malformed(self):
        results = _make_chroma_results(
            ids=["a", "b"],
            documents=["doc a", "doc b"],
            metadatas=[None, None],
            distances=[0.1, 0.2],
        )

        mock_collection = MagicMock()
        mock_collection.query.return_value = results

        with patch("app.services.retrieval.get_embedding", new_callable=AsyncMock, return_value=[0.1] * 384), \
             patch("app.services.retrieval.get_collection", return_value=mock_collection):
            from app.services.retrieval import search as do_search
            output = await do_search("test query", top_k=2)

        assert output == []
