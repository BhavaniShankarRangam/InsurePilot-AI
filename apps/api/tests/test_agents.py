import pytest

from app.ai.agents import get_agent
from app.ai.agents.base import AgentContext, AgentOutput, Confidence
from app.ai.agents.intent import classify_intent, extract_entities
from app.ai.supervisor import guardrails
from app.db.models import AIAction
from app.mcp.registry import ToolContext, registry


@pytest.mark.parametrize("message,agent", [
    ("Explain my home insurance.", "Policy Intelligence Agent"),
    ("Why did my premium increase?", "Renewal Agent"),
    ("Do I need to file this claim?", "Claims Agent"),
    ("Compare my policies.", "Insurance Shopping Agent"),
    ("Show my deductibles.", "Policy Intelligence Agent"),
    ("Why did my health claim get denied?", "Medical Insurance Agent"),
    ("Find coverage gaps.", "Risk Agent"),
    ("Prepare my claim.", "Claims Agent"),
    ("Check my upcoming renewals.", "Renewal Agent"),
    ("Can I get an MRI at this hospital?", "Medical Insurance Agent"),
    ("Is water damage covered?", "Coverage Agent"),
    ("Find an in-network orthopedic doctor", "Provider Network Agent"),
    ("I want to talk to a human", "Human Escalation Agent"),
])
def test_intent_routing(message, agent):
    assert classify_intent(message, {}, {})[0] == agent


def test_entities():
    e = extract_entities("My car repair is $1,200 for claim 39102", {})
    assert e.category == "auto" and e.amount == 1200 and e.claim_ref == "39102"


def _ctx(db, portfolio, message):
    return AgentContext(db=db, user_id=portfolio.user.id, conversation_id=None, message=message, history=[], page={},
                        portfolio=portfolio, entities=extract_entities(message, {}), memory={})


def test_agent_outputs_are_structured_and_cited(db, portfolio):
    out = get_agent("Claims Agent").safe_run(_ctx(db, portfolio, "Why was my home claim denied?"))
    assert isinstance(out, AgentOutput)
    assert out.citations and out.reasoning_summary and out.tools_used
    assert out.confidence in Confidence


def test_agents_cannot_use_unlisted_tools(db, portfolio):
    agent = get_agent("Billing Agent")
    with pytest.raises(PermissionError):
        agent.call(_ctx(db, portfolio, "x"), "submit_claim", claim_ref="39102")


def test_guardrail_blocks_ungrounded_policy_answers():
    out = AgentOutput(agent="X", answer="Your policy covers floods up to $1M.", policy_specific=True,
                      confidence=Confidence.HIGH)
    fixed = guardrails({"output": out, "intent_score": 1})["output"]
    assert fixed.confidence == Confidence.NEEDS_VERIFICATION
    assert "don't have enough verified information" in fixed.answer


def test_external_tools_require_approval(db, demo_user_id):
    ctx = ToolContext(db, demo_user_id, None, "test")
    res = registry.call(ctx, "send_email", to="x@example.com", subject="Hi", body="Body")
    assert res.pending_action_id
    action = db.get(AIAction, res.pending_action_id)
    assert action.status == "pending"  # nothing was sent
    assert action.data_shared and action.what and action.why


def test_read_tool_executes_and_logs(db, demo_user_id):
    res = registry.call(ToolContext(db, demo_user_id, None, "test"), "get_coverages", category="auto")
    assert res.ok and any(c["code"] == "COLL" for c in res.data)


def test_fnol_flow_starts_with_safety(db, portfolio):
    ctx = _ctx(db, portfolio, "Someone hit my car")
    out = get_agent("Claims Agent").safe_run(ctx)
    assert "safe" in out.answer.lower()
    assert ctx.memory["flow"] == "fnol"
