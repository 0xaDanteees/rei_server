from __future__ import annotations

from typing import AsyncGenerator, Dict, Any, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel

from ..security import get_current_user, AuthUser
from ..db import get_db, Base
from ..models import ChatSession, ChatMessage, ChatMemory
from ..llm import get_chat_model

import tiktoken


router = APIRouter()


# Tokenizer utilities
def _get_encoder():
    try:
        return tiktoken.encoding_for_model("gpt-4o-mini")
    except Exception:
        return tiktoken.get_encoding("cl100k_base")


ENCODING = _get_encoder()


def count_tokens(text: str) -> int:
    try:
        return len(ENCODING.encode(text))
    except Exception:
        return len(text) // 4


async def _ensure_owned_session(db: AsyncSession, user_id: UUID, session_id: UUID) -> ChatSession:
    """Verify that the session exists and belongs to the user."""
    stmt = select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)
    res = await db.execute(stmt)
    chat = res.scalars().first()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")
    return chat


async def _load_partner_row(session: AsyncSession, user_id: UUID, partner_id: UUID) -> dict:
    partners_tbl = Base.metadata.tables.get("partners")
    if partners_tbl is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Partners table not available")
    stmt = select(
        partners_tbl.c.id,
        partners_tbl.c.user_id,
        partners_tbl.c.personality_core,
    ).where(partners_tbl.c.id == partner_id, partners_tbl.c.user_id == user_id)
    res = await session.execute(stmt)
    row = res.mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner not found")
    return dict(row)


class CreateSessionIn(BaseModel):
    title: Optional[str] = None


@router.post("/{partner_id}/sessions", status_code=status.HTTP_201_CREATED)
async def create_session(
    partner_id: UUID,
    body: CreateSessionIn,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new chat session for a partner."""
    await _load_partner_row(db, user.user_id, partner_id)
    new_session = ChatSession(
        user_id=user.user_id,
        partner_id=partner_id,
        title=body.title or f"Chat {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
    )
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    return {
        "id": str(new_session.id),
        "title": new_session.title,
        "total_tokens": new_session.total_tokens,
        "created_at": new_session.created_at.isoformat(),
        "updated_at": new_session.updated_at.isoformat() if new_session.updated_at else None,
    }


@router.get("/{partner_id}/sessions")
async def list_sessions(
    partner_id: UUID,
    limit: int = 20,
    offset: int = 0,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await _load_partner_row(session, user.user_id, partner_id)
    stmt = (
        select(ChatSession)
        .where(ChatSession.user_id == user.user_id, ChatSession.partner_id == partner_id)
        .order_by(ChatSession.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    res = await session.execute(stmt)
    items = res.scalars().all()
    return [
        {
            "id": str(it.id),
            "title": it.title,
            "total_tokens": it.total_tokens,
            "created_at": it.created_at.isoformat(),
            "updated_at": it.updated_at.isoformat() if it.updated_at else None,
        }
        for it in items
    ]


@router.get("/sessions/{session_id}/messages")
async def get_messages(
    session_id: UUID,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    chat = await _ensure_owned_session(db, user.user_id, session_id)
    stmt = select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc())
    res = await db.execute(stmt)
    msgs = res.scalars().all()
    return [
        {
            "id": str(m.id),
            "role": m.role,
            "content": m.content,
            "token_count": m.token_count,
            "created_at": m.created_at.isoformat(),
        }
        for m in msgs
    ]


async def _build_system_prompt(personality_core: Optional[dict], memory: Optional[str]) -> str:
    persona_desc = ""
    if personality_core:
        try:
            traits = ", ".join(f"{t.get('trait')}({t.get('rarity')})" for t in personality_core or [])
        except Exception:
            traits = ""
        if traits:
            persona_desc = f"Personality traits: {traits}.\n"
    memory_desc = f"Active memory summary: {memory}\n" if memory else ""
    return (
        "You are an agentic companion optimized for helpful, safe, and concise answers.\n"
        + persona_desc
        + memory_desc
        + "Always be respectful and adapt tone to the user's style."
    )


async def _get_active_memory(db: AsyncSession, session_id: UUID) -> Optional[str]:
    stmt = select(ChatMemory).where(ChatMemory.session_id == session_id, ChatMemory.is_active == True).order_by(ChatMemory.created_at.desc())  # noqa: E712
    res = await db.execute(stmt)
    mem = res.scalars().first()
    return mem.summary if mem else None


async def _create_memory(db: AsyncSession, session_obj: ChatSession) -> None:
    """Summarize the conversation into a new active memory and deactivate previous memories."""
    # Collect last 50 messages for summary
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_obj.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(50)
    )
    res = await db.execute(stmt)
    recent = list(reversed(res.scalars().all()))

    history_text = "\n".join([f"{m.role}: {m.content}" for m in recent])
    sys_prompt = "Summarize the key facts, user preferences, decisions, and next steps from this chat in under 200 words. Keep it partner-agnostic and useful for future turns."
    llm = get_chat_model(streaming=False)
    from langchain_core.prompts import ChatPromptTemplate

    tmpl = ChatPromptTemplate.from_messages([
        ("system", sys_prompt),
        ("human", history_text),
    ])
    summary_msg = await llm.ainvoke(tmpl.format_messages())
    summary = summary_msg.content if hasattr(summary_msg, "content") else str(summary_msg)

    # Deactivate existing memories
    await db.execute(
        update(ChatMemory).where(ChatMemory.session_id == session_obj.id, ChatMemory.is_active == True).values(is_active=False)  # noqa: E712
    )
    db.add(ChatMemory(session_id=session_obj.id, summary=summary, is_active=True))
    # Reset token counter after creating a memory
    session_obj.total_tokens = 0
    session_obj.updated_at = datetime.utcnow()
    await db.commit()


async def _retrieve_context(query: str, partner_id: UUID) -> tuple[str, list[str]]:
    """Placeholder for retrieval. Integrate your vector DB here.
    Returns (context_text, sources_urls)
    """
    # TODO: integrate pgvector/FAISS/etc.
    return "", []


class SendMessageIn(BaseModel):
    message: str
    stream: bool = True


@router.post("/sessions/{session_id}/message")
async def send_message(
    session_id: UUID,
    body: SendMessageIn,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    chat = await _ensure_owned_session(db, user.user_id, session_id)

    # Load partner persona for system prompt
    partner_row = await _load_partner_row(db, user.user_id, chat.partner_id)
    active_memory = await _get_active_memory(db, chat.id)
    system_prompt = await _build_system_prompt(partner_row.get("personality_core"), active_memory)

    # Retrieval step (optional)
    context_text, sources = await _retrieve_context(body.message, chat.partner_id)

    # Persist user message first
    user_tokens = count_tokens(body.message)
    db.add(ChatMessage(session_id=chat.id, role="human", content=body.message, token_count=user_tokens))
    chat.total_tokens += user_tokens
    chat.updated_at = datetime.utcnow()
    await db.commit()

    # Prepare LLM
    llm = get_chat_model(streaming=True)
    from langchain_core.messages import SystemMessage, HumanMessage

    msgs = [SystemMessage(content=system_prompt)]
    if context_text:
        msgs.append(SystemMessage(content=f"Context:\n{context_text}"))
    msgs.append(HumanMessage(content=body.message))

    async def _stream() -> AsyncGenerator[str, None]:
        full_text = ""
        try:
            async for chunk in llm.astream(msgs):
                token = getattr(chunk, "content", None)
                if token:
                    full_text += token
                    yield {"event": "token", "data": token}
        except Exception as e:
            yield {"event": "error", "data": str(e)}
            return

        # After streaming completes, persist AI message and maybe create memory
        ai_tokens = count_tokens(full_text)
        db.add(ChatMessage(session_id=chat.id, role="ai", content=full_text, token_count=ai_tokens))
        chat.total_tokens += ai_tokens
        chat.updated_at = datetime.utcnow()
        await db.commit()

        # Emit sources if any
        if sources:
            yield {"event": "sources", "data": sources}

        # Memory policy: create summary when threshold exceeded
        from ..settings import settings
        if chat.total_tokens >= settings.TOKEN_MEMORY_THRESHOLD:
            await _create_memory(db, chat)
            yield {"event": "memory", "data": "memory_created"}

        yield {"event": "done", "data": ""}

    if body.stream:
        async def _to_sse(gen: AsyncGenerator[Dict[str, Any], None]):
            async for evt in gen:
                # sse-starlette expects plain strings; format as JSON lines
                import json
                yield f"event: {evt['event']}\n" + f"data: {json.dumps(evt['data'])}\n\n"

        return EventSourceResponse(_to_sse(_stream()))

    # Non-streaming fallback: run and return full text
    res = await get_chat_model(streaming=False).ainvoke(msgs)
    full = getattr(res, "content", str(res))
    ai_tokens = count_tokens(full)
    db.add(ChatMessage(session_id=chat.id, role="ai", content=full, token_count=ai_tokens))
    chat.total_tokens += ai_tokens
    chat.updated_at = datetime.utcnow()
    await db.commit()
    return {"message": full, "sources": sources}