"""'Explain This' — plain-English explanations for any complex insurance item, grounded in data."""

from app.services.health_benefits import TERMS
from app.services.health_score import detect_risks
from app.services.portfolio import Portfolio

GLOSSARY = {
    **TERMS,
    "endorsement": "An add-on that changes your policy — it can add coverage back that the main policy excludes.",
    "exclusion": "Something your policy specifically does not cover.",
    "rider": "An optional add-on to a policy (common in life insurance) that adds or changes benefits.",
    "liability_limit": "The most your insurer will pay if you're responsible for injuring someone or damaging their property.",
    "subrogation": "When your insurer recovers money from the person who caused your loss — which can get your deductible back.",
    "fnol": "First Notice of Loss — simply the first time you tell your insurer something happened.",
    "cpt": "A 5-digit code doctors use to describe a procedure. Your plan uses it to decide coverage and price.",
    "premium": "What you pay for your insurance, usually monthly or yearly.",
    "replacement_cost": "Coverage that pays to rebuild or replace with new items, without subtracting for age or wear.",
    "actual_cash_value": "Coverage that pays what something is worth today — the replacement cost minus depreciation.",
}


def _result(simple: str, why: str, nxt: str, actions: list[str], source: str | None, confidence: str) -> dict:
    return {"simple": simple, "why_it_matters": why, "what_happens_next": nxt, "actions": actions, "source": source,
            "confidence": confidence}


def explain(p: Portfolio, kind: str, ref: str | None) -> dict:
    if kind == "term":
        key = (ref or "").lower().replace(" ", "_").replace("-", "_")
        if key in GLOSSARY:
            return _result(GLOSSARY[key], "Knowing this helps you predict what you'll pay and what's protected.",
                           "Nothing — this is just for understanding.", ["Ask a follow-up question"], "InsurePilot glossary", "high")
    if kind in ("coverage", "exclusion", "endorsement"):
        for pol in p.policies:
            items = {"coverage": pol.coverages, "exclusion": pol.exclusions, "endorsement": pol.endorsements}[kind]
            for item in items:
                if item.id == ref:
                    limit = getattr(item, "limit_text", None) or (
                        f"${float(item.limit_amount):,.0f}" if getattr(item, "limit_amount", None) else None)
                    why = {
                        "coverage": f"This is what pays{' up to ' + limit if limit else ''} when this kind of loss happens.",
                        "exclusion": "If a loss falls under this, your insurer may deny the claim — unless an endorsement adds it back.",
                        "endorsement": "It changes the base policy — often adding back coverage that would otherwise be excluded.",
                    }[kind]
                    status = getattr(item, "status", "covered")
                    nxt = ("Consider reviewing this limit with your insurer." if status == "review" else
                           "If you have a loss like this, InsurePilot can help you check whether it applies.")
                    return _result(item.plain_language, why, nxt, ["Ask AI about this", "Find similar coverage"],
                                   f"{pol.carrier.short_name} {pol.product_name} · {item.source_section} · Page {item.source_page}",
                                   "high")
    if kind == "risk":
        for r in detect_risks(p):
            if r.id == ref:
                return _result(r.explanation, "Left alone, this could cost you money or delay a claim.",
                               "Review the details and choose Fix, Remind me later, or Ignore.", r.actions, r.source,
                               "high" if r.certainty == "confirmed" else "needs_verification")
    if kind == "claim_event":
        for c in p.claims:
            for e in c.events:
                if e.id == ref:
                    return _result(f"{e.title}: {e.description or 'This step is part of your claim process.'}",
                                   "Each step moves your claim toward payment.",
                                   "InsurePilot will notify you when the next step happens.", ["Ask about this claim"],
                                   f"Claim {c.claim_number} timeline", "high")
    return _result("I don't have enough verified information to explain this item.", "", "",
                   ["Ask AI", "Talk to a licensed professional"], None, "needs_verification")
