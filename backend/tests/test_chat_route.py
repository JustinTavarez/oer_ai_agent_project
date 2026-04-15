"""Tests confirming the chat flow is independent of ChromaDB."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestChatReturnsResponse:
    def test_chat_returns_response(self):
        with patch(
            "app.routes.chat.get_completion",
            new_callable=AsyncMock,
            return_value={"response": "Here are some OER recommendations."},
        ):
            resp = client.post("/chat", json={"prompt": "Find art resources"})

        assert resp.status_code == 200
        body = resp.json()
        assert "response" in body
        assert body["response"] == "Here are some OER recommendations."


class TestChatSurvivesChromaDown:
    def test_chat_survives_chroma_down(self):
        """Chat should work even when ChromaDB is completely unavailable."""
        with patch(
            "app.routes.chat.get_completion",
            new_callable=AsyncMock,
            return_value={"response": "Recommendations without Chroma."},
        ), patch(
            "app.services.chroma_client.get_chroma_client",
            side_effect=RuntimeError("ChromaDB is down"),
        ):
            resp = client.post("/chat", json={"prompt": "Find art resources"})

        assert resp.status_code == 200
        assert resp.json()["response"] == "Recommendations without Chroma."


class TestChatErrorReturnsGraceful:
    def test_chat_error_returns_friendly_message(self):
        with patch(
            "app.routes.chat.get_completion",
            new_callable=AsyncMock,
            side_effect=Exception("LM Studio unreachable"),
        ):
            resp = client.post("/chat", json={"prompt": "Find art resources"})

        assert resp.status_code == 200
        body = resp.json()
        assert "response" in body
        assert "try again" in body["response"].lower()
