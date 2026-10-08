"""AI risk detection, Insurance Health Score and personalized home layout.

Every finding carries `certainty` ("confirmed" = directly from structured data / documents,
"possible" = inference that needs verification) so uncertain results are never shown as facts.
"""

from dataclasses import asdict, dataclass, field
from datetime import date

from app.db.models import Policy
from app.services.portfolio import Portfolio


@dataclass
class Finding:
    id: str
    kind: str
    title: str
    explanation: str
    severity: str  # attention | review | info
    certainty: str  # confirmed | possible
    category: str
    link: str
    source: str | None = None
    policy_id: str | None = None
    claim_id: str | None = None
    amount: float | None = None
    actions: list[str] = field(default_factory=lambda: ["explain", "fix", "remind", "ignore"])

    def to_dict(self) -> dict:
        return asdict(self)


def _pct(new: float, old: float) -> int:
    return round((new - old) / old * 100) if old else 0


def expected_coinsurance(allowed: float, deductible: float, copay: float, rate: int) -> float:
    return round(max(0.0, allowed - deductible - copay) * rate / 100, 2)


def detect_risks(p: Portfolio) -> list[Finding]:
    out: list[Finding] = []
    today = date.today()

    for pol in p.policies:
        days = (pol.expiration_date - today).days
        if pol.status == "lapsed" or days < 0:
            out.append(Finding(
                f"lapsed-{pol.id}", "coverage_expired", f"{pol.category.title()} coverage has expired",
                f"Your {pol.carrier.short_name} {pol.product_name} ended {abs(days)} days ago. "
                "If you have upcoming trips, you may be unprotected.",
                "info", "confirmed", pol.category, f"/policies/{pol.id}", policy_id=pol.id, actions=["explain", "review", "ignore"]))
            continue
        if days <= 45:
            change = _pct(float(pol.premium_annual), float(pol.prior_premium_annual or pol.premium_annual))
            title = f"{pol.category.title()} policy renews in {days} days"
            if change >= 10:
                title = f"{pol.category.title()} premium increases {change}% at renewal"
            out.append(Finding(
                f"renewal-{pol.id}", "renewal", title,
                f"Your {pol.carrier.short_name} policy renews on {pol.expiration_date:%b %d}. "
                + (f"The premium goes from ${float(pol.prior_premium_annual):,.0f} to ${float(pol.premium_annual):,.0f} per year."
                   if change else "Review it before then."),
                "attention" if change >= 10 else "review", "confirmed", pol.category, f"/policies/{pol.id}?tab=renewal",
                source="Renewal notice", policy_id=pol.id, amount=float(pol.premium_annual) - float(pol.prior_premium_annual or 0),
                actions=["explain", "review", "remind", "ignore"]))

        if pol.category == "home":
            rebuild = float((pol.details or {}).get("rebuild_estimate") or 0)
            cov_a = next((float(c.limit_amount) for c in pol.coverages if c.code == "A" and c.limit_amount), 0.0)
            if rebuild and cov_a and cov_a < rebuild * 0.9:
                ratio = cov_a / rebuild
                out.append(Finding(
                    f"home-gap-{pol.id}", "underinsurance", "Home rebuild coverage may be low",
                    f"Your dwelling coverage is ${cov_a:,.0f}, but the estimated rebuild cost is about ${rebuild:,.0f} "
                    f"({ratio:.0%}). Below 80%, your policy may pay less than full replacement cost on a partial loss. "
                    "Rebuild estimates vary — a carrier appraisal would confirm.",
                    "attention", "possible", "home", f"/policies/{pol.id}", source="Home Policy · Section I — Coverage A · Page 5",
                    policy_id=pol.id, amount=rebuild - cov_a, actions=["explain", "fix", "remind", "ignore"]))

        if pol.category == "life":
            if not any(b.designation == "contingent" for b in pol.beneficiaries):
                out.append(Finding(
                    f"beneficiary-{pol.id}", "missing_beneficiary", "No backup beneficiary on life policy",
                    "If your primary beneficiary can't receive the benefit, the payout may go through probate, which can take months.",
                    "review", "confirmed", "life", f"/policies/{pol.id}", source="Life Policy · Section 2 — Beneficiaries · Page 4",
                    policy_id=pol.id))

    by_cat: dict[str, list[Policy]] = {}
    for pol in p.active_policies:
        by_cat.setdefault(pol.category, []).append(pol)
    for cat, items in by_cat.items():
        if len(items) > 1 and cat not in ("life",):
            out.append(Finding(
                f"dup-{cat}", "duplicate_coverage", f"You may have overlapping {cat} policies",
                f"{len(items)} active {cat} policies were found. They may overlap — or cover different things.",
                "review", "possible", cat, "/compare"))

    for c in p.claims:
        if c.missing_documents and c.status not in ("closed", "paid", "denied"):
            due = next((d for d in c.deadlines), None)
            when = f" by {date.fromisoformat(due['due']):%b %d}" if due else ""
            out.append(Finding(
                f"claim-docs-{c.id}", "missing_claim_document", f"Claim {c.claim_number} needs a document",
                f"Your adjuster is waiting on: {', '.join(c.missing_documents)}. Send it{when} to avoid payment delays.",
                "attention", "confirmed", c.category, f"/claims/{c.id}", source=due["source"] if due else None, claim_id=c.id,
                actions=["explain", "fix", "remind"]))
        if c.status == "denied":
            pol = p.policy_by_id(c.policy_id)
            related = [e for e in (pol.endorsements if pol else []) if "water" in e.name.lower()] if "water" in (c.denial_reason or "").lower() else []
            if related:
                e = related[0]
                out.append(Finding(
                    f"denial-{c.id}", "denial_review", f"Denied claim {c.claim_number} may deserve a second look",
                    f"The denial cites the water exclusion, but your policy also has the {e.name} endorsement "
                    f"(up to ${float(e.limit_amount or 0):,.0f}). Whether it applies depends on the actual cause of loss.",
                    "attention", "possible", c.category, f"/claims/{c.id}", source=f"Endorsement {e.code} · Page {e.source_page}",
                    claim_id=c.id, amount=float(e.limit_amount or 0), actions=["explain", "review", "remind", "ignore"]))

    hp = p.health_plan
    for auth in p.authorizations:
        if auth.status in ("pending", "submitted"):
            missing = [r["item"] for r in auth.requirements if r.get("status") == "missing"]
            out.append(Finding(
                f"auth-{auth.id}", "prior_auth", f"{auth.procedure_name.split(',')[0]} authorization pending",
                f"Decision expected by {auth.decision_due:%b %d}." + (
                    f" One requirement looks incomplete: {', '.join(missing)}. Missing paperwork is a common reason for "
                    "administrative denials." if missing else ""),
                "attention" if missing else "review", "confirmed", "health", "/health?tab=authorizations",
                source="Health Plan Benefits · Section 7 — Prior Authorization · Page 22", actions=["explain", "fix", "remind"]))

    for bill in p.bills:
        for item in bill.line_items:
            if item.get("network_note"):
                out.append(Finding(
                    f"network-{bill.id}-{item['provider'][:8]}", "network_mismatch", "Possible provider-network mismatch",
                    f"{item['provider']} billed ${item['charge']:,.0f} for {item['description'].lower()}, but isn't listed in "
                    f"your plan's directory. Your hospital was in-network — you may be protected from surprise billing.",
                    "review", "possible", "health", "/health?tab=bills", source="Health Plan Benefits · Section 5 — Provider Network · Page 14"))
    if hp:
        for eob in p.eobs:
            exp = expected_coinsurance(float(eob.allowed_amount), float(eob.deductible), float(eob.copay), hp.coinsurance_in_network)
            diff = round(float(eob.coinsurance) - exp, 2)
            if abs(diff) >= 25:
                out.append(Finding(
                    f"eob-{eob.id}", "billing_discrepancy", "Possible billing discrepancy on your knee procedure",
                    f"Your EOB shows ${float(eob.coinsurance):,.0f} coinsurance. At your plan's {hp.coinsurance_in_network}% rate, "
                    f"we'd expect about ${exp:,.0f} — a ${abs(diff):,.0f} difference. It could be an out-of-network line "
                    "or a processing error. Worth asking Bluepeak.",
                    "review", "possible", "health", "/health?tab=bills", source="Explanation of Benefits — Knee Arthroscopy · Page 1",
                    amount=abs(diff), actions=["explain", "fix", "remind", "ignore"]))
    order = {"attention": 0, "review": 1, "info": 2}
    out.sort(key=lambda f: (order[f.severity], f.certainty != "confirmed"))
    return out


def policy_alerts(p: Portfolio, pol: Policy) -> list[dict]:
    return [{"title": f.title, "severity": f.severity} for f in detect_risks(p) if f.policy_id == pol.id or (
        f.claim_id and any(c.id == f.claim_id and c.policy_id == pol.id for c in p.claims)
    ) or (f.category == pol.category and f.kind in ("prior_auth", "network_mismatch", "billing_discrepancy"))]


WEIGHTS = {("attention", "confirmed"): 4, ("attention", "possible"): 3, ("review", "confirmed"): 2,
           ("review", "possible"): 1.5, ("info", "confirmed"): 1, ("info", "possible"): 0.5}


def potential_savings(p: Portfolio) -> dict:
    items: list[dict] = []
    for pol in p.active_policies:
        quotes = [q for q in p.quotes if q.category == pol.category]
        if quotes:
            cheapest = min(quotes, key=lambda q: float(q.premium_annual))
            delta = float(pol.premium_annual) - float(cheapest.premium_annual)
            if delta > 0:
                items.append({"label": f"Lower {pol.category} quote available ({cheapest.carrier_name})", "amount": round(delta),
                              "certainty": "possible", "note": "Coverage differs slightly — compare before switching."})
        for f in (pol.renewal_changes or {}).get("factors", []):
            if "discount removed" in f["label"].lower() and f.get("impact"):
                items.append({"label": "Restore multi-policy discount", "amount": f["impact"], "certainty": "possible",
                              "note": "Requires bundling another policy with the same carrier."})
    for f in detect_risks(p):
        if f.kind == "billing_discrepancy" and f.amount:
            items.append({"label": "Possible billing discrepancy", "amount": round(f.amount), "certainty": "possible",
                          "note": "Only recoverable if the payer confirms an error."})
    return {"total": sum(i["amount"] for i in items), "items": items}


def health_score(p: Portfolio) -> dict:
    risks = detect_risks(p)
    deduction = sum(WEIGHTS[(r.severity, r.certainty)] for r in risks)
    score = max(0, min(100, round(100 - deduction)))
    positives: list[dict] = []
    auto = p.policy("auto")
    if auto and any(c.code == "BI" for c in auto.coverages):
        positives.append({"label": "Auto coverage is healthy — liability, collision and comprehensive in place", "category": "auto"})
    if (h := p.policy("health")) and h.status == "active":
        positives.append({"label": "Health policy active for the full plan year", "category": "health"})
    if (life := p.policy("life")) and life.status == "active":
        positives.append({"label": f"Life insurance in place through {life.expiration_date.year}", "category": "life"})
    if p.policy("pet"):
        positives.append({"label": "Pet coverage active for Miso", "category": "pet"})
    band = "healthy" if score >= 85 else "good" if score >= 70 else "needs_attention"
    return {
        "score": score,
        "band": band,
        "headline": {
            "healthy": "Your insurance looks healthy.",
            "good": "Your insurance is in good shape, with a few things to review.",
            "needs_attention": "A few items need your attention.",
        }[band],
        "positives": positives,
        "factors": [{"label": r.title, "severity": r.severity, "certainty": r.certainty, "category": r.category,
                     "impact": -WEIGHTS[(r.severity, r.certainty)]} for r in risks],
        "disclaimer": "The Insurance Health Score is guidance based on your data, not financial or legal advice.",
    }


def home_layout(p: Portfolio) -> list[str]:
    """Order of dashboard sections, most relevant first."""
    sections: list[tuple[int, str]] = [(50, "summary"), (60, "actions"), (70, "wallet"), (80, "insights")]
    today = date.today()
    if any(c.status in ("submitted", "in_review") and (today - c.incident_date).days <= 21 for c in p.claims):
        sections.append((10, "claims"))
    if any(0 <= (pol.expiration_date - today).days <= 30 for pol in p.active_policies):
        sections.append((20, "renewal"))
    if any(a.status in ("pending", "submitted") for a in p.authorizations):
        sections.append((30, "health"))
    return [s for _, s in sorted(sections)]


def daily_summary(p: Portfolio) -> dict:
    risks = [r for r in detect_risks(p) if r.severity != "info"]
    name = p.user.preferred_name or p.user.full_name.split()[0]
    if not risks:
        return {"greeting_name": name, "headline": "Everything looks good today.", "items": []}
    attention = [r for r in risks if r.severity == "attention"]
    review = len(risks) - len(attention)
    head = f"{len(attention)} item{'s' if len(attention) != 1 else ''} need{'s' if len(attention) == 1 else ''} your attention"
    head += f", and {review} {'is' if review == 1 else 'are'} worth reviewing." if review else "."
    return {"greeting_name": name, "headline": head, "items": [r.title for r in risks[:3]]}
