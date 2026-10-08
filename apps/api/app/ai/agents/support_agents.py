import re

from app.ai.agents.base import AgentContext, AgentOutput, BaseAgent, Card, Confidence
from app.ai.llm.base import Task
from app.services.communication import draft


class CommunicationAgent(BaseAgent):
    name = "Communication Agent"
    description = "Drafts editable emails, adjuster questions, appeals and dispute messages. Never sends without approval."
    tools = ("get_claim", "get_policy")

    def run(self, ctx: AgentContext) -> AgentOutput:
        p = ctx.portfolio
        low = ctx.lower
        claim = (p.claim_by_ref(ctx.entities.claim_ref) if ctx.entities.claim_ref else None)
        if "appeal" in low or "reconsider" in low:
            kind, claim = "appeal", claim or next((c for c in p.claims if c.status == "denied"), None)
        elif "question" in low and "adjuster" in low:
            kind, claim = "adjuster_questions", claim or next((c for c in p.claims if c.status == "denied"), None)
        elif any(k in low for k in ("bill", "dispute", "eob", "billing")):
            kind = "billing_dispute"
        elif any(k in low for k in ("renewal", "discount", "premium")):
            kind = "renewal_inquiry"
        elif any(k in low for k in ("provider", "imaging", "doctor")):
            kind = "provider_inquiry"
        elif "adjuster" in low or "claim" in low:
            kind, claim = "claim_email", claim or (p.open_claims[0] if p.open_claims else None)
        else:
            kind = "policy_clarification"
        self.status(ctx, "analyzing", "Drafting your message")
        if claim:
            self.call(ctx, "get_claim", claim_ref=claim.id)
        policy = p.policy(ctx.entities.category or "auto") if kind == "renewal_inquiry" else None
        msg = draft(p, kind, claim=claim, policy=policy)
        return self.output(
            answer=f"Here's a draft **{kind.replace('_', ' ')}**. Edit anything you like — **nothing is sent until you "
                   "review and approve it.**",
            task=Task.DRAFTING, confidence=Confidence.HIGH,
            reasoning_summary="Drafted from your claim/policy data using only facts on file.",
            cards=[Card(type="draft", data=msg)], data_used=["Claim and policy data"], evidence=[msg["body"]],
            suggestions=["Make it shorter", "Make it more formal"],
        )


SCAM_SIGNALS = {
    "gift card": "Requests for gift-card payment", "wire": "Requests to wire money", "bitcoin": "Requests for crypto payment",
    "urgent": "Pressure to act urgently", "verify your account": "Requests to 'verify your account'",
    "password": "Requests for your password", "click this link": "Unexpected payment links", "ssn": "Requests for your SSN",
    "social security": "Requests for your Social Security number",
}


class FraudSignalAgent(BaseAgent):
    name = "Fraud Signal Agent"
    description = "Flags scam/phishing signals in messages and inconsistencies in claim data. Never accuses."
    tools = ("get_claim",)

    def run(self, ctx: AgentContext) -> AgentOutput:
        low = ctx.lower
        signals = [label for key, label in SCAM_SIGNALS.items() if key in low]
        domains = re.findall(r"@([\w.-]+)", ctx.message)
        carriers = {pol.carrier.short_name.lower() for pol in ctx.portfolio.policies}
        odd_domains = [d for d in domains if not any(c in d.lower() for c in carriers)]
        if odd_domains:
            signals.append(f"Sender domain not matching your carriers ({', '.join(odd_domains)})")
        if not signals:
            return self.output(
                answer="I didn't spot common scam signals in what you shared. To be safe, contact your insurer using the "
                       "phone number on your policy documents — not a number from the message.",
                confidence=Confidence.MODERATE, reasoning_summary="Checked for common phishing and payment-scam patterns.",
                limitations=["Absence of signals doesn't prove a message is legitimate."])
        lines = "\n".join(f"- ⚠️ {s}" for s in signals)
        phones = "\n".join(f"- {pol.carrier.name}: {pol.carrier.phone}" for pol in ctx.portfolio.active_policies[:4])
        return self.output(
            answer=f"This message shows some **warning signs**:\n\n{lines}\n\nDon't pay or share information yet. "
                   f"Contact your insurer directly using a verified number:\n\n{phones}",
            confidence=Confidence.MODERATE, reasoning_summary="Matched known scam patterns; verified carrier contacts from "
                                                              "your policies.",
            cards=[Card(type="fraud_signals", data={"signals": signals})], evidence=[lines],
            limitations=["These are risk signals, not a determination of fraud."],
        )


class HumanEscalationAgent(BaseAgent):
    name = "Human Escalation Agent"
    description = "Hands off to a licensed professional with a concise, privacy-minimized case summary."
    tools = ("request_human_review",)

    def run(self, ctx: AgentContext) -> AgentOutput:
        p = ctx.portfolio
        topic = ctx.memory.get("last_topic") or ctx.message
        summary = {
            "topic": topic[:200],
            "open_items": [c.title for c in p.open_claims] + [c.title for c in p.claims if c.status == "denied"],
            "policies": [f"{pol.category}: {pol.carrier.short_name}" for pol in p.active_policies],
        }
        res = self.call(ctx, "request_human_review", topic=topic[:200], summary=str(summary))
        return self.output(
            answer="I can connect you with a **licensed insurance professional**. I've prepared a short case summary so you "
                   "don't have to repeat yourself. **Approve the request below** and someone will reach out within one "
                   "business day.",
            confidence=Confidence.HUMAN_REVIEW, reasoning_summary="Prepared a privacy-minimized handoff summary.",
            cards=[Card(type="escalation", data=summary)], action_ids=[res.pending_action_id] if res.pending_action_id else [],
            evidence=[str(summary)],
        )
