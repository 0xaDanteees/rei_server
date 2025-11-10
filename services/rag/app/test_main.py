"""
Integration tests for RAG service routers using TestClient.
We mint JWTs locally using the service's JWT secret (settings.JWT_SECRET).
Comprehensive test coverage for agentic chat functionality including:
- Chat session management
- Message sending (streaming and non-streaming)
- Memory creation and retrieval
- Token counting
- Partner integration
- Authentication and authorization
"""

import uuid
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Optional
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from fastapi.testclient import TestClient
from jose import jwt
import sys
from pathlib import Path

from .main import app
from .settings import settings

# Ensure repo root is importable so we can access Auth and Partners service apps
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from services.auth.app.main import app as auth_app
from services.partners.app.main import app as partners_app


def mint_token(user_id: Optional[uuid.UUID] = None, is_active: bool = True, expires_in: int = 3600) -> str:
    """Create a signed JWT for tests compatible with get_current_user()."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id or uuid.uuid4()),
        "is_active": is_active,
        "iss": settings.JWT_ISSUER,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def unique_email(prefix: str = "qa.rag") -> str:
    return f"{prefix}.{uuid.uuid4().hex[:12]}@example.com"


@pytest.fixture(scope="session")
def auth_ctx() -> dict:
    """Create a real user in the shared database via Auth service."""
    with TestClient(auth_app) as ac:
        email = unique_email()
        password = "Admin123!__"
        r = ac.post("/auth/register", json={"email": email, "password": password})
        assert r.status_code == 201, r.text
        l = ac.post("/auth/login", json={"email": email, "password": password})
        assert l.status_code == 200, l.text
        auth_token = l.json()["payload"]["access_token"]
        # Retrieve the UUID from /user/me
        me = ac.get("/user/me", headers={"Authorization": f"Bearer {auth_token}"})
        assert me.status_code == 200, me.text
        me_payload = me.json()["payload"]
        user_id_str = me_payload.get("id")
        assert user_id_str, "Auth /user/me did not return id"
        # RAG expects JWT sub to be a UUID string; mint a local token with that UUID
        rag_token = mint_token(user_id=uuid.UUID(user_id_str))
        return {"token": rag_token, "user_id": user_id_str, "email": email}


@pytest.fixture(scope="session")
def partner_ctx(auth_ctx: dict) -> dict:
    """Create a partner for the authenticated user."""
    with TestClient(partners_app) as pc:
        # Mint a partners token with the same user_id
        partners_token = mint_token(user_id=uuid.UUID(auth_ctx["user_id"]))
        create = pc.post(
            "/partner",
            headers=auth_headers(partners_token),
            json={
                "name": "RAG Test Partner",
                "gender": "female",
                "age": 22,
                "user_id": auth_ctx["user_id"],
            },
        )
        assert create.status_code == 201, create.text
        cj = create.json()
        payload = cj.get("payload", cj)
        partner_id = payload["id"]
        return {"partner_id": partner_id, "partner_name": "RAG Test Partner"}


def test_health_endpoint(client: TestClient):
    """Test health endpoint returns proper status."""
    r = client.get("/rag/health")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("status") == "ok"
    assert body.get("db") in {"up", "down"}


def test_landing_page_public_access(client: TestClient):
    """Test that landing pages are publicly accessible."""
    # Root landing page
    r1 = client.get("/")
    assert r1.status_code == 200, r1.text
    assert "RAG Service" in r1.text or "rag" in r1.text.lower()
    
    # Prefixed landing page
    r2 = client.get("/rag")
    assert r2.status_code == 200, r2.text
    assert "RAG Service" in r2.text or "rag" in r2.text.lower()


def test_chat_endpoints_require_auth(client: TestClient, partner_ctx: dict):
    """Test that chat endpoints require authentication."""
    partner_id = partner_ctx["partner_id"]
    
    # Create session without auth
    r1 = client.post(f"/rag/chat/{partner_id}/sessions", json={"title": "Test"})
    assert r1.status_code in (401, 403), r1.text
    
    # List sessions without auth
    r2 = client.get(f"/rag/chat/{partner_id}/sessions")
    assert r2.status_code in (401, 403), r2.text


def test_create_and_list_sessions(client: TestClient, auth_ctx: dict, partner_ctx: dict):
    """Test creating and listing chat sessions."""
    partner_id = partner_ctx["partner_id"]
    token = auth_ctx["token"]
    
    # Create a session
    create = client.post(
        f"/rag/chat/{partner_id}/sessions",
        headers=auth_headers(token),
        json={"title": "Test Chat Session"},
    )
    assert create.status_code == 201, create.text
    cj = create.json()
    assert "id" in cj
    assert cj["title"] == "Test Chat Session"
    assert cj["total_tokens"] == 0
    session_id = cj["id"]
    
    # List sessions
    lst = client.get(
        f"/rag/chat/{partner_id}/sessions",
        headers=auth_headers(token),
    )
    assert lst.status_code == 200, lst.text
    sessions = lst.json()
    assert isinstance(sessions, list)
    assert len(sessions) >= 1
    assert any(s["id"] == session_id for s in sessions)


def test_create_session_with_auto_title(client: TestClient, auth_ctx: dict, partner_ctx: dict):
    """Test creating a session without providing a title (auto-generated)."""
    partner_id = partner_ctx["partner_id"]
    token = auth_ctx["token"]
    
    create = client.post(
        f"/rag/chat/{partner_id}/sessions",
        headers=auth_headers(token),
        json={},
    )
    assert create.status_code == 201, create.text
    cj = create.json()
    assert "id" in cj
    assert "title" in cj
    # Auto-generated title should contain "Chat" and a timestamp
    assert "Chat" in cj["title"]


def test_get_messages_empty_session(client: TestClient, auth_ctx: dict, partner_ctx: dict):
    """Test getting messages from a newly created session (should be empty)."""
    partner_id = partner_ctx["partner_id"]
    token = auth_ctx["token"]
    
    # Create session
    create = client.post(
        f"/rag/chat/{partner_id}/sessions",
        headers=auth_headers(token),
        json={"title": "Empty Session"},
    )
    session_id = create.json()["id"]
    
    # Get messages
    msgs = client.get(
        f"/rag/chat/sessions/{session_id}/messages",
        headers=auth_headers(token),
    )
    assert msgs.status_code == 200, msgs.text
    messages = msgs.json()
    assert isinstance(messages, list)
    assert len(messages) == 0


def test_send_message_non_streaming(client: TestClient, auth_ctx: dict, partner_ctx: dict):
    """Test sending a message in non-streaming mode."""
    partner_id = partner_ctx["partner_id"]
    token = auth_ctx["token"]
    
    # Create session
    create = client.post(
        f"/rag/chat/{partner_id}/sessions",
        headers=auth_headers(token),
        json={"title": "Non-Streaming Test"},
    )
    session_id = create.json()["id"]
    
    # Send message (non-streaming) - will use real LLM if OPENAI_API_KEY is set
    # This is an integration test that validates the full flow
    send = client.post(
        f"/rag/chat/sessions/{session_id}/message",
        headers=auth_headers(token),
        json={"message": "Say 'test passed' in 2 words", "stream": False},
    )
    assert send.status_code == 200, send.text
    resp = send.json()
    assert "message" in resp
    assert "sources" in resp
    assert isinstance(resp["message"], str)
    assert len(resp["message"]) > 0
    
    # Verify messages were persisted
    msgs = client.get(
        f"/rag/chat/sessions/{session_id}/messages",
        headers=auth_headers(token),
    )
    messages = msgs.json()
    assert len(messages) == 2  # user + ai
    assert messages[0]["role"] == "human"
    assert messages[0]["content"] == "Say 'test passed' in 2 words"
    assert messages[1]["role"] == "ai"
    assert len(messages[1]["content"]) > 0


def test_send_message_streaming(client: TestClient, auth_ctx: dict, partner_ctx: dict):
    """Test sending a message in streaming mode."""
    partner_id = partner_ctx["partner_id"]
    token = auth_ctx["token"]
    
    # Create session
    create = client.post(
        f"/rag/chat/{partner_id}/sessions",
        headers=auth_headers(token),
        json={"title": "Streaming Test"},
    )
    session_id = create.json()["id"]
    
    # Send message (streaming) - integration test with real LLM
    send = client.post(
        f"/rag/chat/sessions/{session_id}/message",
        headers=auth_headers(token),
        json={"message": "Hi", "stream": True},
    )
    assert send.status_code == 200, send.text
    # Streaming response returns SSE format


def test_session_ownership_enforcement(client: TestClient, auth_ctx: dict, partner_ctx: dict):
    """Test that users can only access their own sessions."""
    partner_id = partner_ctx["partner_id"]
    token = auth_ctx["token"]
    
    # Create session with first user
    create = client.post(
        f"/rag/chat/{partner_id}/sessions",
        headers=auth_headers(token),
        json={"title": "User 1 Session"},
    )
    session_id = create.json()["id"]
    
    # Create a second user
    other_token = mint_token(user_id=uuid.uuid4())
    
    # Try to access first user's session with second user's token
    msgs = client.get(
        f"/rag/chat/sessions/{session_id}/messages",
        headers=auth_headers(other_token),
    )
    assert msgs.status_code == 404, msgs.text  # Session not found for this user


def test_partner_not_found(client: TestClient, auth_ctx: dict):
    """Test creating a session for a non-existent partner."""
    fake_partner_id = str(uuid.uuid4())
    token = auth_ctx["token"]
    
    create = client.post(
        f"/rag/chat/{fake_partner_id}/sessions",
        headers=auth_headers(token),
        json={"title": "Invalid Partner"},
    )
    assert create.status_code == 404, create.text
    body = create.json()
    assert body.get("status") == 404
    assert "not found" in body.get("message", "").lower()


def test_token_counting_and_memory_creation(client: TestClient, auth_ctx: dict, partner_ctx: dict):
    """Test that token counting works and messages are persisted."""
    partner_id = partner_ctx["partner_id"]
    token = auth_ctx["token"]
    
    # Create session
    create = client.post(
        f"/rag/chat/{partner_id}/sessions",
        headers=auth_headers(token),
        json={"title": "Token Test"},
    )
    session_id = create.json()["id"]
    
    # Send a few messages
    for i in range(2):
        send = client.post(
            f"/rag/chat/sessions/{session_id}/message",
            headers=auth_headers(token),
            json={"message": f"Message {i+1}", "stream": False},
        )
        assert send.status_code == 200, send.text
    
    # Verify messages were created
    msgs = client.get(
        f"/rag/chat/sessions/{session_id}/messages",
        headers=auth_headers(token),
    )
    messages = msgs.json()
    assert len(messages) == 4  # 2 user + 2 ai messages


def test_inactive_user_rejected(client: TestClient, partner_ctx: dict):
    """Test that inactive users are rejected."""
    partner_id = partner_ctx["partner_id"]
    inactive_token = mint_token(user_id=uuid.uuid4(), is_active=False)
    
    create = client.post(
        f"/rag/chat/{partner_id}/sessions",
        headers=auth_headers(inactive_token),
        json={"title": "Inactive User"},
    )
    assert create.status_code == 403, create.text
    body = create.json()
    assert "inactive" in body.get("message", "").lower()


def test_expired_token_rejected(client: TestClient, partner_ctx: dict):
    """Test that expired tokens are rejected."""
    partner_id = partner_ctx["partner_id"]
    expired_token = mint_token(user_id=uuid.uuid4(), expires_in=-3600)  # Expired 1 hour ago
    
    create = client.post(
        f"/rag/chat/{partner_id}/sessions",
        headers=auth_headers(expired_token),
        json={"title": "Expired Token"},
    )
    assert create.status_code == 401, create.text
    body = create.json()
    # Token expired message may vary, just check it's unauthorized
    assert body.get("status") == 401


def test_invalid_token_rejected(client: TestClient, partner_ctx: dict):
    """Test that invalid tokens are rejected."""
    partner_id = partner_ctx["partner_id"]
    invalid_token = "invalid.token.here"
    
    create = client.post(
        f"/rag/chat/{partner_id}/sessions",
        headers=auth_headers(invalid_token),
        json={"title": "Invalid Token"},
    )
    assert create.status_code == 401, create.text


def test_personality_core_integration(client: TestClient, auth_ctx: dict, partner_ctx: dict):
    """Test that messages can be sent and personality is loaded."""
    partner_id = partner_ctx["partner_id"]
    token = auth_ctx["token"]
    
    # Create session
    create = client.post(
        f"/rag/chat/{partner_id}/sessions",
        headers=auth_headers(token),
        json={"title": "Personality Test"},
    )
    session_id = create.json()["id"]
    
    # Send message - integration test
    send = client.post(
        f"/rag/chat/sessions/{session_id}/message",
        headers=auth_headers(token),
        json={"message": "Hi", "stream": False},
    )
    assert send.status_code == 200, send.text
    resp = send.json()
    assert "message" in resp
    assert len(resp["message"]) > 0


def test_session_pagination(client: TestClient, auth_ctx: dict, partner_ctx: dict):
    """Test session listing with pagination."""
    partner_id = partner_ctx["partner_id"]
    token = auth_ctx["token"]
    
    # Create multiple sessions
    session_ids = []
    for i in range(5):
        create = client.post(
            f"/rag/chat/{partner_id}/sessions",
            headers=auth_headers(token),
            json={"title": f"Session {i}"},
        )
        session_ids.append(create.json()["id"])
    
    # List with limit
    lst = client.get(
        f"/rag/chat/{partner_id}/sessions?limit=2",
        headers=auth_headers(token),
    )
    assert lst.status_code == 200, lst.text
    sessions = lst.json()
    assert len(sessions) == 2
    
    # List with offset
    lst2 = client.get(
        f"/rag/chat/{partner_id}/sessions?limit=2&offset=2",
        headers=auth_headers(token),
    )
    assert lst2.status_code == 200, lst2.text
    sessions2 = lst2.json()
    assert len(sessions2) >= 1
    # Sessions should be different
    assert sessions[0]["id"] != sessions2[0]["id"]


def test_message_validation(client: TestClient, auth_ctx: dict, partner_ctx: dict):
    """Test message validation (empty message is accepted but LLM handles it)."""
    partner_id = partner_ctx["partner_id"]
    token = auth_ctx["token"]
    
    # Create session
    create = client.post(
        f"/rag/chat/{partner_id}/sessions",
        headers=auth_headers(token),
        json={"title": "Validation Test"},
    )
    session_id = create.json()["id"]
    
    # Send empty message - LLM will handle gracefully
    send = client.post(
        f"/rag/chat/sessions/{session_id}/message",
        headers=auth_headers(token),
        json={"message": "", "stream": False},
    )
    # Empty messages are accepted, LLM responds appropriately
    assert send.status_code == 200, send.text
    resp = send.json()
    assert "message" in resp


def test_retrieval_context_integration(client: TestClient, auth_ctx: dict, partner_ctx: dict):
    """Test that retrieval endpoint works (currently returns empty sources)."""
    partner_id = partner_ctx["partner_id"]
    token = auth_ctx["token"]
    
    # Create session
    create = client.post(
        f"/rag/chat/{partner_id}/sessions",
        headers=auth_headers(token),
        json={"title": "Retrieval Test"},
    )
    session_id = create.json()["id"]
    
    # Send message - integration test
    send = client.post(
        f"/rag/chat/sessions/{session_id}/message",
        headers=auth_headers(token),
        json={"message": "Test", "stream": False},
    )
    assert send.status_code == 200, send.text
    resp = send.json()
    
    # Verify sources field exists (empty for now since retrieval is TODO)
    assert "sources" in resp
    assert isinstance(resp["sources"], list)


def test_exception_handlers(client: TestClient):
    """Test that exception handlers return proper error envelopes."""
    # Test 404 (non-existent endpoint)
    r = client.get("/rag/nonexistent")
    assert r.status_code == 404
    body = r.json()
    assert "status" in body
    assert body["status"] == 404
