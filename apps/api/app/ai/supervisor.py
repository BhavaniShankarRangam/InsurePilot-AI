"""LangGraph supervisor: understand → route to a specialist agent → guardrails."""

from functools import lru_cache
from typing import TypedDict

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from app.ai.agents import AGENT_CLASSES, get_agent
from app.ai.agents.base import AgentContext, AgentOutput, Confidence
from app.ai.agents.intent import classify_intent


class SupervisorState(TypedDict, total=False):
    ctx: AgentContext
    agent: str
    intent_score: float
    output: AgentOutput


def _node_key(agent_name: str) -> str:
    return agent_name.lower().replace(" ", "_")


def understand(state: SupervisorState) -> SupervisorState:
    ctx = state["ctx"]
    writer = get_stream_writer()
    ctx.emit = writer
    writer({"type": "status", "state": "understanding", "label": "Understanding your request"})
    agent, score = classify_intent(ctx.message, ctx.page, ctx.memory)
    writer({"type": "route", "agent": agent})
    return {"agent": agent, "intent_score": score}


def make_agent_node(agent_name: str):
    def node(state: SupervisorState) -> SupervisorState:
        ctx = state["ctx"]
        ctx.emit = get_stream_writer()
        return {"output": get_agent(agent_name).safe_run(ctx)}

    node.__name__ = _node_key(agent_name)
    return node


def guardrails(state: SupervisorState) -> SupervisorState:
    """Enforce the AI rules: no ungrounded policy answers, fallbacks for low confidence, escalation offers."""
    out = state["output"].model_copy(deep=True)
    grounded = bool(out.citations or out.data_used)
    if out.policy_specific and not grounded:
        out.answer = ("I don't have enough verified information to answer this confidently. I couldn't find this in your "
                      "policy data or documents.")
        out.confidence = Confidence.NEEDS_VERIFICATION
        out.limitations.append("No supporting policy data or document was found.")
    if out.confidence == Confidence.NEEDS_VERIFICATION:
        for s in ("Retrieve another document", "Tell me more details", "Talk to a licensed professional"):
            if s not in out.suggestions:
                out.suggestions.append(s)
    if (out.escalate or out.confidence == Confidence.HUMAN_REVIEW) and "Talk to a licensed professional" not in out.suggestions:
        out.suggestions.append("Talk to a licensed professional")
    if state.get("intent_score", 1) == 0 and out.confidence == Confidence.HIGH:
        out.limitations.append("I interpreted your request using the page you're on.")
    return {"output": out}


@lru_cache
def build_supervisor():
    g = StateGraph(SupervisorState)
    g.add_node("understand", understand)
    routes: dict[str, str] = {}
    for cls in AGENT_CLASSES:
        key = _node_key(cls.name)
        g.add_node(key, make_agent_node(cls.name))
        g.add_edge(key, "guardrails")
        routes[cls.name] = key
    g.add_node("guardrails", guardrails)
    g.add_edge(START, "understand")
    g.add_conditional_edges("understand", lambda s: s["agent"], routes)
    g.add_edge("guardrails", END)
    return g.compile()
