from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, TimestampMixin, utcnow


class AIConversation(IdMixin, TimestampMixin, Base):
    __tablename__ = "ai_conversations"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(160), default="New conversation")
    memory: Mapped[dict] = mapped_column(JSON, default=dict)  # short-term facts carried across turns
    messages: Mapped[list["AIMessage"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="AIMessage.created_at"
    )


class AIMessage(IdMixin, Base):
    __tablename__ = "ai_messages"

    conversation_id: Mapped[str] = mapped_column(ForeignKey("ai_conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(12))  # user|assistant
    content: Mapped[str] = mapped_column(Text)
    agent: Mapped[str | None] = mapped_column(String(60))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)  # citations, cards, confidence, actions
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    conversation: Mapped[AIConversation] = relationship(back_populates="messages")


class AIAction(IdMixin, TimestampMixin, Base):
    """A proposed high-impact action that requires human approval before execution."""

    __tablename__ = "ai_actions"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(32))
    kind: Mapped[str] = mapped_column(String(40))  # submit_claim|send_email|change_policy|share_medical_data|...
    title: Mapped[str] = mapped_column(String(200))
    what: Mapped[str] = mapped_column(Text)
    why: Mapped[str] = mapped_column(Text)
    data_shared: Mapped[list] = mapped_column(JSON, default=list)
    recipient: Mapped[str | None] = mapped_column(String(160))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|approved|executed|cancelled|failed
    risk_level: Mapped[str] = mapped_column(String(10), default="high")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result: Mapped[dict] = mapped_column(JSON, default=dict)


class AIToolExecution(IdMixin, Base):
    __tablename__ = "ai_tool_executions"

    user_id: Mapped[str] = mapped_column(String(32), index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(32), index=True)
    agent: Mapped[str] = mapped_column(String(60))
    tool: Mapped[str] = mapped_column(String(80))
    summary: Mapped[str] = mapped_column(String(240))
    ok: Mapped[bool] = mapped_column(Boolean, default=True)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class LLMUsage(IdMixin, Base):
    __tablename__ = "llm_usage"

    user_id: Mapped[str | None] = mapped_column(String(32), index=True)
    provider: Mapped[str] = mapped_column(String(20))
    model: Mapped[str] = mapped_column(String(60))
    task: Mapped[str] = mapped_column(String(40))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class Notification(IdMixin, TimestampMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(20))
    priority: Mapped[int] = mapped_column(Integer, default=2)  # 1 = highest
    link: Mapped[str | None] = mapped_column(String(200))
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    snoozed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EvaluationRun(IdMixin, TimestampMixin, Base):
    __tablename__ = "evaluation_runs"

    suite: Mapped[str] = mapped_column(String(60))
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    cases: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text)


class GraphEdge(IdMixin, Base):
    """Knowledge-graph triple backing the Insurance Digital Twin (User owns Vehicle, ...)."""

    __tablename__ = "graph_edges"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    subject_type: Mapped[str] = mapped_column(String(30))
    subject_id: Mapped[str] = mapped_column(String(32), index=True)
    predicate: Mapped[str] = mapped_column(String(40))
    object_type: Mapped[str] = mapped_column(String(30))
    object_id: Mapped[str] = mapped_column(String(32), index=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
