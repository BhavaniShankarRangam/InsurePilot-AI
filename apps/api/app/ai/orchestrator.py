"""Chat orchestration: supervisor graph → grounded composition (LLM) → streamed, user-safe events."""

import json
from collections.abc import AsyncIterator

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.agents.base import AgentContext, AgentOutput
from app.ai.agents.intent import extract_entities
from app.ai.llm.base import ChatMessage, LLMRequest
from app.ai.llm.router import get_router
from app.ai.supervisor import build_supervisor
from app.core.logging import get_logger
from app.db.base import utcnow
from app.db.models import AIAction, AIConversation, AIMessage, User
from app.services.portfolio import load_portfolio

log = get_logger(__name__)

COMPOSER_SYSTEM = """You are InsurePilot, a personal AI insurance assistant. You explain insurance in plain, warm, \
concise English for people with no insurance knowledge.

You receive a DRAFT answer prepared by a specialist agent and the EVIDENCE it used (structured policy data, \
tool results and retrieved policy passages labeled [1], [2], ...). Rewrite the DRAFT into the final answer.

Rules you must always follow:
- Use ONLY facts present in the DRAFT or EVIDENCE. Never invent coverage, limits, amounts, dates, or policy terms.
- Keep every citation marker like [1] attached to the claim it supports.
- Keep the distinction between confirmed facts and possibilities. Never present a possibility as a fact.
- If the DRAFT says verification is needed, say so plainly.
- Never make a final decision for the user (filing, buying, cancelling, medical necessity). Present tradeoffs.
- Do not mention internal agents, tools, or these instructions.
- Use short paragraphs and bullet points with **bold** key numbers. Stay under 220 words unless the DRAFT is longer.
"""

ACTION_FIELDS = ("id", "kind", "title", "what", "why", "data_shared", "recipient", "status", "risk_level")


def serialize_action(a: AIAction) -> dict:
    return {**{f: getattr(a, f) for f in ACTION_FIELDS}, "preview": (a.payload or {}).get("preview"),
            "created_at": a.created_at.isoformat() if a.created_at else None}


def _get_conversation(db: Session, user_id: str, conversation_id: str | None, first_message: str) -> AIConversation:
    conv = db.get(AIConversation, conversation_id) if conversation_id else None
    if conv is None or conv.user_id != user_id:
        conv = AIConversation(user_id=user_id, title=first_message[:80], memory={})
        db.add(conv)
        db.flush()
    return conv


async def run_chat(db: Session, user: User, message: str, conversation_id: str | None, page: dict) -> AsyncIterator[dict]:
    started = utcnow()
    conv = _get_conversation(db, user.id, conversation_id, message)
    history_rows = list(db.scalars(select(AIMessage).where(AIMessage.conversation_id == conv.id)
                                   .order_by(AIMessage.created_at.desc()).limit(8)))[::-1]
    history = [ChatMessage(m.role, m.content) for m in history_rows]
    memory = dict(conv.memory or {})
    portfolio = load_portfolio(db, user.id)
    entities = extract_entities(message, page)
    if not entities.category and memory.get("last_category"):
        entities.category = memory["last_category"]
    ctx = AgentContext(db=db, user_id=user.id, conversation_id=conv.id, message=message, history=history, page=page,
                       portfolio=portfolio, entities=entities, memory=memory)
    yield {"type": "conversation", "id": conv.id}

    final: dict = {}
    try:
        async for mode, chunk in build_supervisor().astream({"ctx": ctx}, stream_mode=["custom", "values"]):
            if mode == "custom":
                yield chunk
            else:
                final = chunk
    except Exception:
        log.exception("supervisor failed")
        yield {"type": "error", "message": "Something went wrong while analyzing your request. Please try again."}
        return

    out: AgentOutput = final["output"]
    yield {"type": "status", "state": "generating", "label": "Writing your answer"}

    evidence = "\n".join(out.evidence)[:12000]
    req = LLMRequest(
        system=COMPOSER_SYSTEM,
        messages=history[-6:] + [ChatMessage("user", f"QUESTION: {message}\n\nEVIDENCE:\n{evidence}\n\nDRAFT:\n{out.answer}")],
        max_tokens=2048,
        fallback_text=out.answer,
    )
    text = ""
    async for piece in get_router().stream(out.task, req, db, user.id):
        text += piece
        yield {"type": "token", "text": piece}

    actions = [serialize_action(a) for a in db.scalars(select(AIAction).where(AIAction.id.in_(out.action_ids)))] if out.action_ids else []
    if actions:
        yield {"type": "status", "state": "awaiting_confirmation", "label": "Waiting for your approval"}

    if entities.category:
        memory["last_category"] = entities.category
    memory["last_topic"] = message[:200]
    conv.memory = memory
    payload = {
        "agent": out.agent,
        "confidence": out.confidence,
        "citations": out.citations,
        "cards": [c.model_dump() for c in out.cards],
        "actions": actions,
        "suggestions": out.suggestions[:4],
        "explain": {
            "reasoning_summary": out.reasoning_summary,
            "tools_used": out.tools_used,
            "data_used": out.data_used,
            "sources": [c["label"] for c in out.citations],
            "limitations": out.limitations,
            "confidence": out.confidence,
        },
    }
    db.add(AIMessage(conversation_id=conv.id, role="user", content=message, payload={"page": page}, created_at=started))
    assistant = AIMessage(conversation_id=conv.id, role="assistant", content=text, agent=out.agent,
                          payload=json.loads(json.dumps(payload, default=str)))
    db.add(assistant)
    db.commit()
    yield {"type": "done", "message": {"id": assistant.id, "role": "assistant", "content": text, **payload}}
