"""Tool catalog exposed to agents (and to MCP clients via app/mcp/server.py)."""

from datetime import date

from app.db.models import AIAction, Claim, Policy
from app.integrations.adapters import (
    MockCarrierAdapter,
    MockEmailSender,
    MockFHIRPayerAdapter,
    MockProviderDirectory,
    MockQuoteMarketplace,
)
from app.mcp.registry import ToolContext, ToolSpec, registry
from app.rag.retriever import HybridRetriever, RetrievalFilters
from app.services import claims as claim_svc
from app.services import health_benefits as hb
from app.services.policy_intel import coverage_profile, explain_policy
from app.services.portfolio import load_portfolio


def _policy(ctx: ToolContext, policy_id: str | None = None, category: str | None = None) -> Policy:
    p = load_portfolio(ctx.db, ctx.user_id)
    pol = p.policy_by_id(policy_id) if policy_id else p.policy(category or "")
    if pol is None:
        raise LookupError("policy not found")
    return pol


def _claim(ctx: ToolContext, claim_ref: str) -> Claim:
    c = load_portfolio(ctx.db, ctx.user_id).claim_by_ref(claim_ref)
    if c is None:
        raise LookupError("claim not found")
    return c


def get_policy(ctx: ToolContext, policy_id: str | None = None, category: str | None = None) -> dict:
    pol = _policy(ctx, policy_id, category)
    return {**explain_policy(pol), "carrier_api": MockCarrierAdapter(ctx.db).fetch_policy(pol)}


def get_coverages(ctx: ToolContext, policy_id: str | None = None, category: str | None = None) -> list[dict]:
    pol = _policy(ctx, policy_id, category)
    return [{"code": c.code, "name": c.name, "limit": c.limit_text, "deductible": float(c.deductible) if c.deductible else None,
             "status": c.status, "plain_language": c.plain_language, "source": f"{c.source_section} · Page {c.source_page}"}
            for c in pol.coverages]


def get_deductible(ctx: ToolContext, category: str, coverage_code: str | None = None) -> dict:
    pol = _policy(ctx, category=category)
    cov = next((c for c in pol.coverages if coverage_code and c.code == coverage_code), None)
    return {"policy_deductible": float(pol.deductible or 0),
            "coverage_deductibles": {c.name: float(c.deductible) for c in pol.coverages if c.deductible},
            "requested": {"name": cov.name, "deductible": float(cov.deductible or 0)} if cov else None}


def get_claim(ctx: ToolContext, claim_ref: str) -> dict:
    c = _claim(ctx, claim_ref)
    return {"id": c.id, "claim_number": c.claim_number, "title": c.title, "status": c.status, "stage": c.stage,
            "incident_date": c.incident_date.isoformat(), "amount_claimed": float(c.amount_claimed or 0),
            "missing_documents": c.missing_documents, "denial_reason": c.denial_reason, "deadlines": c.deadlines,
            "events": [{"title": e.title, "status": e.status, "at": e.occurred_at.isoformat()} for e in c.events]}


def get_claim_status(ctx: ToolContext, claim_ref: str) -> dict:
    return MockCarrierAdapter(ctx.db).claim_status(_claim(ctx, claim_ref))


def get_policy_documents(ctx: ToolContext, policy_id: str | None = None) -> list[dict]:
    p = load_portfolio(ctx.db, ctx.user_id)
    return [{"id": d.id, "title": d.title, "type": d.doc_type, "pages": d.page_count} for d in p.documents
            if policy_id is None or d.policy_id == policy_id]


def search_policy_documents(ctx: ToolContext, query: str, category: str | None = None, claim_id: str | None = None,
                            top_k: int = 4) -> list[dict]:
    filters = RetrievalFilters(user_id=ctx.user_id, categories=[category] if category else None, claim_id=claim_id)
    hits = HybridRetriever(ctx.db).search(query, filters, top_k=top_k)
    return [{"citation": h.citation().to_dict(), "score": round(h.score, 3), "text": h.compressed} for h in hits]


def get_bill(ctx: ToolContext) -> list[dict]:
    p = load_portfolio(ctx.db, ctx.user_id)
    return [{"id": b.id, "service": b.service_description, "total_charge": float(b.total_charge), "amount_due": float(b.amount_due),
             "due_date": b.due_date.isoformat() if b.due_date else None, "line_items": b.line_items} for b in p.bills]


def get_eob(ctx: ToolContext) -> list[dict]:
    p = load_portfolio(ctx.db, ctx.user_id)
    fhir = MockFHIRPayerAdapter()
    return [fhir.explanation_of_benefit(e) | {"id": e.id} for e in p.eobs]


def get_provider_network_status(ctx: ToolContext, provider_name: str) -> dict:
    p = load_portfolio(ctx.db, ctx.user_id)
    directory = MockProviderDirectory(ctx.db)
    matches = directory.search(provider_name)
    if not matches or p.health_plan is None:
        return {"found": False}
    return {"found": True, **directory.network_status(matches[0], p.health_plan.network_name)}


def find_providers(ctx: ToolContext, query: str, in_network_only: bool = True) -> list[dict]:
    p = load_portfolio(ctx.db, ctx.user_id)
    network = p.health_plan.network_name if p.health_plan else None
    out = []
    for pr in MockProviderDirectory(ctx.db).search(query):
        in_net = bool(network and network in (pr.networks or []))
        if in_network_only and not in_net:
            continue
        out.append({"id": pr.id, "name": pr.name, "specialty": pr.specialty, "city": pr.city, "in_network": in_net,
                    "rating": float(pr.rating or 0)})
    return out


def get_prior_authorization_status(ctx: ToolContext) -> list[dict]:
    p = load_portfolio(ctx.db, ctx.user_id)
    return [hb.prior_auth_assistant(p, a) for a in p.authorizations]


def check_procedure_cost(ctx: ToolContext, procedure: str, provider_name: str = "") -> dict:
    return hb.procedure_check(load_portfolio(ctx.db, ctx.user_id), procedure, provider_name)


def reconcile_medical_bill(ctx: ToolContext) -> dict:
    p = load_portfolio(ctx.db, ctx.user_id)
    if not p.bills or not p.eobs:
        return {"available": False}
    return hb.reconcile(p, p.bills[0], p.eobs[0])


def get_quotes(ctx: ToolContext, category: str) -> list[dict]:
    pol = _policy(ctx, category=category)
    quotes = MockQuoteMarketplace(ctx.db).quotes(ctx.user_id, category, coverage_profile(pol))
    return [{"carrier": q.carrier_name, "premium": float(q.premium_annual), "coverages": q.coverages} for q in quotes]


def create_claim_draft(ctx: ToolContext, category: str, title: str, description: str, incident_date: str | None = None,
                       amount: float | None = None) -> dict:
    pol = _policy(ctx, category=category)
    claim = claim_svc.create_claim_draft(ctx.db, ctx.user_id, pol, title, description,
                                         date.fromisoformat(incident_date) if incident_date else date.today(), amount)
    return {"claim_id": claim.id, "claim_number": claim.claim_number, "status": claim.status}


def generate_claim_packet(ctx: ToolContext, claim_ref: str) -> dict:
    p = load_portfolio(ctx.db, ctx.user_id)
    return claim_svc.claim_packet(p, _claim(ctx, claim_ref))


# ---- External actions (executed only after approval) ----------------------
def submit_claim(ctx: ToolContext, claim_ref: str) -> dict:
    claim = _claim(ctx, claim_ref)
    p = load_portfolio(ctx.db, ctx.user_id)
    return MockCarrierAdapter(ctx.db).submit_claim(claim, claim_svc.claim_packet(p, claim))


def send_email(ctx: ToolContext, to: str, subject: str, body: str) -> dict:
    return MockEmailSender().send(to, subject, body)


def share_medical_data(ctx: ToolContext, recipient: str, items: list[str]) -> dict:
    return {"shared_with": recipient, "items": items, "status": "shared (simulated)"}


def request_human_review(ctx: ToolContext, topic: str, summary: str) -> dict:
    return {"ticket": f"HR-{abs(hash(topic)) % 10**6:06d}", "status": "queued", "sla": "1 business day"}


def _approval_human(ctx: ToolContext, args: dict) -> dict:
    return {"title": "Request help from a licensed professional",
            "what": "Open a case with a licensed insurance professional and share a short summary.",
            "why": "Some questions need a human expert's judgment.",
            "data_shared": ["Your question", "Names of your policies and open claims (no ID numbers)"],
            "recipient": "InsurePilot licensed advisor team", "risk": "medium"}


def _approval_submit_claim(ctx: ToolContext, args: dict) -> dict:
    c = _claim(ctx, args["claim_ref"])
    return {"title": f"Submit claim {c.claim_number} to your insurer",
            "what": f"Send the claim packet for “{c.title}” to your insurer for processing.",
            "why": "Submitting starts the insurer's review. You asked InsurePilot to prepare this claim.",
            "data_shared": ["Claim description and incident date", "Attached photos and documents", "Policy number"],
            "recipient": "Your insurer's claims department"}


def _approval_send_email(ctx: ToolContext, args: dict) -> dict:
    return {"title": f"Send email: {args.get('subject', '')}", "what": f"Email {args.get('to')} with the draft you reviewed.",
            "why": "You asked InsurePilot to contact this party on your behalf.",
            "data_shared": ["Your name", "Email body as shown"], "recipient": args.get("to"),
            "payload": {"preview": args.get("body", "")[:1200]}}


def _approval_share(ctx: ToolContext, args: dict) -> dict:
    return {"title": f"Share medical information with {args.get('recipient')}", "what": "Share the selected health documents.",
            "why": "Needed to resolve your billing or authorization question.", "data_shared": args.get("items", []),
            "recipient": args.get("recipient"), "risk": "high"}


def _s(fmt: str):
    return lambda args, result: fmt.format(**{k: v for k, v in args.items() if isinstance(v, str | int | float)})


S = {"type": "string"}
_SPECS = [
    ToolSpec("get_policy", "Get a policy's plain-language explanation by id or category.",
             {"type": "object", "properties": {"policy_id": S, "category": S}}, "read", get_policy,
             lambda a, r: f"Retrieved {r['title']}"),
    ToolSpec("get_coverages", "List a policy's coverages, limits and deductibles with sources.",
             {"type": "object", "properties": {"policy_id": S, "category": S}}, "read", get_coverages,
             lambda a, r: f"Retrieved {len(r)} coverages"),
    ToolSpec("get_deductible", "Get deductibles for a policy category.",
             {"type": "object", "properties": {"category": S, "coverage_code": S}, "required": ["category"]}, "read",
             get_deductible, _s("Analyzed {category} deductibles")),
    ToolSpec("get_claim", "Get full details for a claim by id or number.",
             {"type": "object", "properties": {"claim_ref": S}, "required": ["claim_ref"]}, "read", get_claim,
             lambda a, r: f"Retrieved claim {r['claim_number']}"),
    ToolSpec("get_claim_status", "Get live claim status from the carrier.",
             {"type": "object", "properties": {"claim_ref": S}, "required": ["claim_ref"]}, "read", get_claim_status,
             lambda a, r: f"Checked status of claim {r['claim_number']}"),
    ToolSpec("get_policy_documents", "List documents attached to policies.",
             {"type": "object", "properties": {"policy_id": S}}, "read", get_policy_documents,
             lambda a, r: f"Found {len(r)} documents"),
    ToolSpec("search_policy_documents", "Hybrid search over the user's policy documents with citations.",
             {"type": "object", "properties": {"query": S, "category": S, "claim_id": S}, "required": ["query"]}, "read",
             search_policy_documents, lambda a, r: f"Searched documents ({len(r)} passages)"),
    ToolSpec("get_bill", "Get medical bills.", {"type": "object", "properties": {}}, "read", get_bill,
             lambda a, r: f"Retrieved {len(r)} bills"),
    ToolSpec("get_eob", "Get Explanation of Benefits (FHIR ExplanationOfBenefit).", {"type": "object", "properties": {}},
             "read", get_eob, lambda a, r: f"Retrieved {len(r)} EOBs"),
    ToolSpec("get_provider_network_status", "Check whether a provider is in the user's health network.",
             {"type": "object", "properties": {"provider_name": S}, "required": ["provider_name"]}, "read",
             get_provider_network_status, lambda a, r: "Checked provider network status"),
    ToolSpec("find_providers", "Search the provider directory.",
             {"type": "object", "properties": {"query": S, "in_network_only": {"type": "boolean"}}, "required": ["query"]},
             "read", find_providers, lambda a, r: f"Found {len(r)} providers"),
    ToolSpec("get_prior_authorization_status", "Get prior authorization requests and missing requirements.",
             {"type": "object", "properties": {}}, "read", get_prior_authorization_status,
             lambda a, r: f"Checked {len(r)} authorization(s)"),
    ToolSpec("check_procedure_cost", "Estimate cost/network/authorization for a procedure at a provider.",
             {"type": "object", "properties": {"procedure": S, "provider_name": S}, "required": ["procedure"]}, "read",
             check_procedure_cost, lambda a, r: "Estimated procedure cost"),
    ToolSpec("reconcile_medical_bill", "Compare a hospital bill with the insurer's EOB.", {"type": "object", "properties": {}},
             "read", reconcile_medical_bill, lambda a, r: "Compared hospital bill with EOB"),
    ToolSpec("get_quotes", "Fetch comparable quotes for a category from the marketplace.",
             {"type": "object", "properties": {"category": S}, "required": ["category"]}, "read", get_quotes,
             lambda a, r: f"Fetched {len(r)} quotes"),
    ToolSpec("create_claim_draft", "Create an internal claim draft (not submitted).",
             {"type": "object", "properties": {"category": S, "title": S, "description": S, "incident_date": S,
                                               "amount": {"type": "number"}}, "required": ["category", "title", "description"]},
             "draft", create_claim_draft, lambda a, r: f"Prepared claim draft {r['claim_number']}"),
    ToolSpec("generate_claim_packet", "Assemble a claim packet with documents and timeline.",
             {"type": "object", "properties": {"claim_ref": S}, "required": ["claim_ref"]}, "draft", generate_claim_packet,
             lambda a, r: f"Prepared claim packet for {r['claim_number']}"),
    ToolSpec("submit_claim", "Submit a claim to the insurer. Requires user approval.",
             {"type": "object", "properties": {"claim_ref": S}, "required": ["claim_ref"]}, "external", submit_claim,
             approval=_approval_submit_claim),
    ToolSpec("send_email", "Send an email to an insurer/provider. Requires user approval.",
             {"type": "object", "properties": {"to": S, "subject": S, "body": S}, "required": ["to", "subject", "body"]},
             "external", send_email, approval=_approval_send_email),
    ToolSpec("share_medical_data", "Share medical documents with a third party. Requires user approval.",
             {"type": "object", "properties": {"recipient": S, "items": {"type": "array", "items": S}},
              "required": ["recipient", "items"]}, "external", share_medical_data, approval=_approval_share),
    ToolSpec("request_human_review", "Escalate to a licensed professional. Requires user approval.",
             {"type": "object", "properties": {"topic": S, "summary": S}, "required": ["topic", "summary"]}, "external",
             request_human_review, approval=_approval_human),
]

for _spec in _SPECS:
    registry.register(_spec)

__all__ = ["registry", "AIAction"]
