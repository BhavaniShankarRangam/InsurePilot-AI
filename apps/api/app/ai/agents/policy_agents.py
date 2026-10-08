from datetime import date

from app.ai.agents.base import AgentContext, AgentOutput, BaseAgent, Card, Confidence
from app.ai.llm.base import Task
from app.rag.text import tokenize
from app.services.health_score import detect_risks, health_score, potential_savings
from app.services.policy_intel import compare, coverage_profile, explain_policy, premium_change, renewal_autopilot

CATEGORY_NAMES = {"auto": "auto", "home": "home", "health": "health", "life": "life", "pet": "pet", "travel": "travel",
                  "renters": "renters", "commercial": "business"}


def _m(v) -> str:
    return f"${float(v):,.0f}"


class PolicyIntelligenceAgent(BaseAgent):
    name = "Policy Intelligence Agent"
    description = "Explains policies, deductibles and limits in plain English."
    tools = ("get_policy", "get_coverages", "get_deductible", "search_policy_documents", "get_policy_documents")

    def run(self, ctx: AgentContext) -> AgentOutput:
        p = ctx.portfolio
        if "deductible" in ctx.lower and not ctx.entities.categories:
            return self._deductibles(ctx)
        category = ctx.entities.category or ctx.page.get("category")
        if ctx.page.get("policy_id") and not ctx.entities.categories:
            pol = p.policy_by_id(ctx.page["policy_id"])
            category = pol.category if pol else category
        if not category:
            return self._overview(ctx)
        if "deductible" in ctx.lower:
            return self._deductibles(ctx, [category])
        self.status(ctx, "retrieving", f"Retrieving your {CATEGORY_NAMES.get(category, category)} policy")
        res = self.call(ctx, "get_policy", category=category)
        if not res.ok:
            return self.fallback(ctx, f"I couldn't find a {category} policy in your account.")
        info = res.data
        self.status(ctx, "analyzing", "Analyzing coverage")
        hits = self.search(ctx, f"{category} declarations coverage limits {ctx.message}", category=category, top_k=2, min_score=0.2)
        covered = "\n".join(f"- **{c['name']}** — {c['detail']}" for c in info["covered"][:5])
        not_cov = "\n".join(f"- **{c['name']}** — {c['detail']}" for c in info["not_covered"][:3])
        gaps = "".join(f"\n\n⚠️ **Worth reviewing:** {g['name']} — {g['detail']}" for g in info["potential_gaps"])
        endorse = "".join(f"\n\n➕ **Extra protection:** {e['name']} — {e['detail']}" for e in info["endorsements"])
        cite = " " + " ".join(self.cite(h) for h in hits) if hits else ""
        answer = (
            f"Here's your **{info['title']}** in plain English{cite}.\n\n**What you're covered for**\n{covered}\n\n"
            f"**What's not covered**\n{not_cov or '- No major exclusions found in your data.'}{endorse}{gaps}\n\n"
            f"Your deductible is **{info['deductible']}**, the premium is **{_m(info['premium'])}/year**, and it renews on "
            f"**{date.fromisoformat(info['renewal_date']):%B %d, %Y}**."
        )
        return self.output(
            answer=answer, task=Task.COVERAGE_EXPLANATION, policy_specific=True,
            confidence=Confidence.HIGH if hits else Confidence.MODERATE,
            reasoning_summary="Combined your structured policy data with the matching sections of your policy document.",
            cards=[Card(type="policy_explainer", data=info)],
            data_used=[f"{info['title']} (structured policy data)"],
            evidence=[f"Policy data: {info}"],
            suggestions=["What's not covered?", "Why did my premium change?", "Find coverage gaps"],
        )

    def _deductibles(self, ctx: AgentContext, categories: list[str] | None = None) -> AgentOutput:
        self.status(ctx, "retrieving", "Retrieving your deductibles")
        rows: list[dict] = []
        cats = categories or [pol.category for pol in ctx.portfolio.active_policies]
        for cat in cats:
            res = self.call(ctx, "get_deductible", category=cat)
            if res.ok:
                for name, amt in res.data["coverage_deductibles"].items():
                    rows.append({"category": cat, "name": name, "amount": amt})
                if not res.data["coverage_deductibles"] and res.data["policy_deductible"]:
                    rows.append({"category": cat, "name": "Policy deductible", "amount": res.data["policy_deductible"]})
        hp = ctx.portfolio.health_plan
        hits = self.search(ctx, f"{ctx.message} deductible", category=cats[0] if len(cats) == 1 else None,
                           top_k=2, min_score=0.2)
        cite = " " + " ".join(self.cite(h) for h in hits) if hits else ""
        lines = "\n".join(f"- **{r['category'].title()} · {r['name']}:** {_m(r['amount'])}" for r in rows)
        extra = ""
        if hp and (not categories or "health" in categories):
            left = float(hp.deductible_individual) - float(hp.deductible_met)
            extra = f"\n\nFor health, you've already met **{_m(hp.deductible_met)}** of your {_m(hp.deductible_individual)} deductible — only **{_m(left)}** left this year."
        return self.output(
            answer=f"Here are your deductibles — the amount you pay before insurance pays on a claim{cite}:\n\n{lines}{extra}",
            task=Task.SUMMARY, confidence=Confidence.HIGH, policy_specific=True,
            reasoning_summary="Read deductibles directly from your structured policy data.",
            cards=[Card(type="deductibles", data={"rows": rows})], data_used=["Structured policy data"],
            evidence=[f"Deductibles: {rows}"], suggestions=["What if I raise my auto deductible to $2,000?", "Explain coinsurance"],
        )

    def _overview(self, ctx: AgentContext) -> AgentOutput:
        p = ctx.portfolio
        lines = "\n".join(
            f"- **{pol.category.title()}** · {pol.carrier.short_name} {pol.product_name} — {pol.summary}"
            + (" *(expired)*" if pol.status == "lapsed" else "") for pol in p.policies)
        return self.output(
            answer=f"You have **{len(p.active_policies)} active policies**:\n\n{lines}\n\nAsk me about any of them — "
                   "for example, “Explain my home insurance.”",
            confidence=Confidence.HIGH, policy_specific=True,
            reasoning_summary="Summarized all policies in your Insurance Digital Twin.",
            data_used=["Insurance Digital Twin"], evidence=[lines],
            suggestions=["Explain my home insurance", "Show my deductibles", "Find coverage gaps"],
        )


class CoverageAgent(BaseAgent):
    name = "Coverage Agent"
    description = "Answers 'am I covered for…' questions strictly from policy data and documents."
    tools = ("get_coverages", "search_policy_documents", "get_policy")

    def run(self, ctx: AgentContext) -> AgentOutput:
        p = ctx.portfolio
        category = ctx.entities.category
        q = set(tokenize(ctx.message))
        self.status(ctx, "retrieving", "Searching coverages, exclusions and endorsements")
        matches: list[dict] = []
        for pol in p.active_policies:
            if category and pol.category != category:
                continue
            for c in pol.coverages:
                if q & set(tokenize(f"{c.name} {c.plain_language}")):
                    matches.append({"kind": "coverage", "status": c.status, "name": c.name, "detail": c.plain_language,
                                    "policy": pol.product_name, "source": f"{c.source_section} · Page {c.source_page}"})
            for e in pol.exclusions:
                if q & set(tokenize(f"{e.name} {e.plain_language}")):
                    matches.append({"kind": "exclusion", "status": "not_covered", "name": e.name, "detail": e.plain_language,
                                    "policy": pol.product_name, "source": f"{e.source_section} · Page {e.source_page}"})
            for e in pol.endorsements:
                if q & set(tokenize(f"{e.name} {e.plain_language}")):
                    matches.append({"kind": "endorsement", "status": "partial", "name": e.name, "detail": e.plain_language,
                                    "policy": pol.product_name, "source": f"{e.source_section} · Page {e.source_page}"})
        hits = self.search(ctx, ctx.message, category=category, top_k=3)
        if not matches and not hits:
            return self.fallback(ctx, "I couldn't find anything in your policies about that. I can check another "
                                      "document if you upload it, or connect you with a licensed agent.")
        self.status(ctx, "analyzing", "Matching your question to policy language")
        order = {"coverage": 0, "endorsement": 1, "exclusion": 2}
        matches.sort(key=lambda m: order[m["kind"]])
        icon = {"covered": "✅", "partial": "🟡", "not_covered": "⛔", "review": "🔍"}
        lines = "\n".join(f"- {icon.get(m['status'], '•')} **{m['name']}** ({m['policy']}) — {m['detail']}" for m in matches[:5])
        quotes = "\n".join(f"> {h['text'][:260]} {self.cite(h)}" for h in hits[:2])
        has_conflict = any(m["kind"] == "exclusion" for m in matches) and any(m["kind"] != "exclusion" for m in matches)
        answer = (
            f"Here's what your policy says:\n\n{lines}\n\n{quotes}"
            + ("\n\nBecause both a coverage/endorsement and an exclusion may apply, the outcome depends on the exact cause "
               "of the loss. An adjuster makes the final determination." if has_conflict else "")
        )
        conf = Confidence.HIGH if matches and hits and not has_conflict else Confidence.MODERATE
        return self.output(
            answer=answer, task=Task.COVERAGE_EXPLANATION, confidence=conf, policy_specific=True,
            reasoning_summary="Matched your question against coverages, exclusions and endorsements, then confirmed with "
                              "the policy text.",
            cards=[Card(type="coverage_matches", data={"items": matches[:6]})],
            data_used=["Policy coverages, exclusions and endorsements"], evidence=[f"Matches: {matches[:6]}"],
            limitations=["Coverage decisions are made by your insurer based on the facts of a loss."],
            suggestions=["Explain this endorsement", "What's my deductible for this?"],
        )


class RenewalAgent(BaseAgent):
    name = "Renewal Agent"
    description = "Detects renewals, explains premium changes, finds discounts and alternatives."
    tools = ("get_policy", "search_policy_documents", "get_quotes")

    def run(self, ctx: AgentContext) -> AgentOutput:
        p = ctx.portfolio
        upcoming = sorted((pol for pol in p.active_policies if (pol.expiration_date - date.today()).days <= 60),
                          key=lambda x: x.expiration_date)
        explicit = ctx.entities.categories[0] if ctx.entities.categories else None
        by_increase = sorted(upcoming or p.active_policies, key=lambda x: -(float(x.premium_annual) - float(x.prior_premium_annual or x.premium_annual)))
        target = p.policy(explicit) if explicit else (by_increase[0] if by_increase else None)
        if target is None:
            return self.output(answer="You don't have any renewals in the next 60 days. 🎉", confidence=Confidence.HIGH,
                               reasoning_summary="Checked expiration dates on all active policies.")
        self.status(ctx, "retrieving", f"Retrieving your {target.category} renewal notice")
        self.call(ctx, "get_policy", policy_id=target.id)
        self.status(ctx, "analyzing", "Comparing with your previous premium")
        pc = premium_change(target)
        hits = self.search(ctx, "renewal premium change factors surcharge discount", category=target.category, top_k=1)
        cite = self.cite(hits[0]) if hits else ""
        confirmed = "\n".join(f"- ✅ {f['label']}" + (f" (+{_m(f['impact'])}/yr)" if f.get("impact") else "") for f in pc["confirmed"])
        possible = "\n".join(f"- ❔ {f['label']}" for f in pc["possible"])
        quotes = self.call(ctx, "get_quotes", category=target.category).data or []
        cheaper = [q for q in quotes if q["premium"] < pc["current_premium"]]
        others = "\n".join(f"- {u.category.title()} renews {u.expiration_date:%b %d}" for u in upcoming if u.id != target.id)
        reasons = (f"**Confirmed reasons** (from your carrier's renewal notice {cite}):\n{confirmed}\n\n" if confirmed else
                   "Your carrier hasn't stated reasons in the documents I have. I can draft a message asking them.\n\n")
        answer = (
            f"Your **{target.category} premium is going from {_m(pc['prior_premium'])} to {_m(pc['current_premium'])}** "
            f"per year ({pc['change_percent']:+d}%). It renews on **{target.expiration_date:%B %d}**.\n\n"
            + reasons
            + (f"**Possible factors** (not stated by your carrier):\n{possible}\n\n" if possible else "")
            + (f"I also found **{len(cheaper)} comparable quotes** for less. Nothing changes unless you approve it."
               if cheaper else "")
            + (f"\n\nOther upcoming renewals:\n{others}" if others else "")
        )
        return self.output(
            answer=answer, task=Task.CROSS_DOCUMENT, confidence=Confidence.HIGH if hits else Confidence.MODERATE,
            policy_specific=True,
            reasoning_summary="Compared the prior and renewal premium, separated reasons stated by your carrier from "
                              "general possibilities, and checked alternatives.",
            cards=[Card(type="premium_change", data=pc), Card(type="renewal", data=renewal_autopilot(p, target))],
            data_used=["Renewal notice", "Prior term premium", "Marketplace quotes (mock)"],
            evidence=[f"Premium change data: {pc}"],
            suggestions=[f"Compare {target.category} quotes", "Draft an email asking about discounts",
                         "What if I raise my deductible to $2,000?"],
        )


class ShoppingAgent(BaseAgent):
    name = "Insurance Shopping Agent"
    description = "Builds a coverage profile and compares normalized quotes objectively."
    tools = ("get_policy", "get_quotes")

    def run(self, ctx: AgentContext) -> AgentOutput:
        category = ctx.entities.category or "auto"
        pol = ctx.portfolio.policy(category)
        if pol is None:
            return self.fallback(ctx, f"I don't see a {category} policy to build a coverage profile from.")
        self.status(ctx, "retrieving", "Building your coverage profile")
        self.call(ctx, "get_policy", policy_id=pol.id)
        self.status(ctx, "tool", "Requesting comparable quotes")
        self.call(ctx, "get_quotes", category=category)
        self.status(ctx, "analyzing", "Normalizing coverages")
        cmp = compare(ctx.portfolio, category)
        lines = "\n".join(f"- **{t['name']}:** " + "; ".join(t["notes"]) for t in cmp["tradeoffs"])
        return self.output(
            answer=f"I built a coverage profile from your current {category} policy and compared "
                   f"**{len(cmp['columns']) - 1} quotes** side by side.\n\n{lines}\n\n"
                   "I don't rank carriers — the right choice depends on what you value (price, rental coverage, "
                   "roadside, deductibles). Switching would always need your approval.",
            task=Task.POLICY_COMPARISON, confidence=Confidence.MODERATE,
            reasoning_summary="Normalized each quote to the same coverage fields as your current policy and listed "
                              "objective differences.",
            cards=[Card(type="comparison", data=cmp), Card(type="coverage_profile", data=coverage_profile(pol))],
            data_used=["Current policy", "Marketplace quotes (mock)"], evidence=[f"Comparison: {cmp['tradeoffs']}"],
            limitations=["Quotes are estimates from a mock marketplace and may change after underwriting."],
            suggestions=["Which has the best rental coverage?", "What would I lose by switching?"],
        )


class RiskAgent(BaseAgent):
    name = "Risk Agent"
    description = "Detects coverage gaps, expirations, discrepancies and other risks."
    tools = ("get_coverages", "search_policy_documents")

    def run(self, ctx: AgentContext) -> AgentOutput:
        self.status(ctx, "analyzing", "Scanning your policies for gaps and risks")
        p = ctx.portfolio
        risks = detect_risks(p)
        hs = health_score(p)
        savings = potential_savings(p)
        if not risks:
            return self.output(answer="I didn't find any gaps or risks. Your insurance looks healthy. ✅",
                               confidence=Confidence.HIGH, reasoning_summary="Checked all risk rules.")
        hits = self.search(ctx, "coverage A dwelling replacement cost 80%", category="home", top_k=1) if any(
            r.kind == "underinsurance" for r in risks) else []
        icon = {"attention": "🔴", "review": "🟡", "info": "⚪"}
        lines = "\n".join(
            f"- {icon[r.severity]} **{r.title}** — {r.explanation}"
            + (" *(possible — needs verification)*" if r.certainty == "possible" else "") for r in risks[:6])
        answer = (f"Your Insurance Health Score is **{hs['score']}/100**. {hs['headline']}\n\n{lines}"
                  + (f"\n\nRebuild rule {self.cite(hits[0])}." if hits else "")
                  + (f"\n\nPotential savings found: up to **{_m(savings['total'])}** (estimates)." if savings["total"] else ""))
        return self.output(
            answer=answer, task=Task.CROSS_DOCUMENT, confidence=Confidence.MODERATE, policy_specific=True,
            reasoning_summary="Ran gap, expiration, duplicate, beneficiary, deadline, network and billing checks across "
                              "your portfolio. Items marked “possible” are inferences.",
            cards=[Card(type="risks", data={"items": [r.to_dict() for r in risks]}), Card(type="health_score", data=hs)],
            data_used=["All policies", "Claims", "Bills & EOBs", "Authorizations"], evidence=[lines],
            limitations=["Rebuild-cost estimates vary; a carrier appraisal is more accurate."],
            suggestions=["Fix the home coverage gap", "Explain the billing discrepancy", "Add a backup beneficiary"],
        )


class BillingAgent(BaseAgent):
    name = "Billing Agent"
    description = "Premium payments, due dates and billing questions."
    tools = ("get_policy",)

    def run(self, ctx: AgentContext) -> AgentOutput:
        from sqlalchemy import select

        from app.db.models import Payment

        self.status(ctx, "retrieving", "Retrieving your payment schedule")
        pays = list(ctx.db.scalars(select(Payment).where(Payment.user_id == ctx.user_id, Payment.status == "scheduled")
                                   .order_by(Payment.due_date)))
        pol_names = {pol.id: f"{pol.category.title()} ({pol.carrier.short_name})" for pol in ctx.portfolio.policies}
        lines = "\n".join(f"- **{pol_names.get(x.policy_id, 'Policy')}:** {_m(x.amount)} on {x.due_date:%b %d} "
                          f"(card ending {x.method_last4})" for x in pays)
        total = sum(float(pol.premium_annual) for pol in ctx.portfolio.active_policies)
        return self.output(
            answer=f"Your upcoming premium payments:\n\n{lines or '- None scheduled'}\n\nYou spend about **{_m(total)}/year** "
                   f"(≈{_m(total / 12)}/month) on insurance. Payments are never made without your approval.",
            confidence=Confidence.HIGH, reasoning_summary="Read your scheduled payments and active premiums.",
            cards=[Card(type="payments", data={"items": [{"policy": pol_names.get(x.policy_id), "amount": float(x.amount),
                                                          "due": x.due_date.isoformat()} for x in pays]})],
            data_used=["Payment schedule"], evidence=[lines], suggestions=["Why did my premium increase?"],
        )


class DocumentIntelligenceAgent(BaseAgent):
    name = "Document Intelligence Agent"
    description = "Classifies, summarizes and extracts deadlines, amounts and action items from documents."
    tools = ("get_policy_documents", "search_policy_documents")

    def run(self, ctx: AgentContext) -> AgentOutput:
        p = ctx.portfolio
        doc_id = ctx.page.get("document_id")
        doc = next((d for d in p.documents if d.id == doc_id), None)
        self.status(ctx, "retrieving", "Reading your documents")
        self.call(ctx, "get_policy_documents")
        if doc:
            ex = doc.extracted or {}
            amounts = ", ".join(_m(a) for a in ex.get("monetary_amounts", [])[:5]) or "none found"
            actions = "\n".join(f"- {a}" for a in ex.get("action_items", [])) or "- None found"
            deadlines = ", ".join(ex.get("deadlines", [])) or "none found"
            return self.output(
                answer=f"**{doc.title}** — {doc.summary}\n\n**Amounts:** {amounts}\n\n**Deadlines:** {deadlines}\n\n"
                       f"**What you may need to do:**\n{actions}",
                confidence=Confidence.MODERATE if doc.classification_confidence != "high" else Confidence.HIGH,
                reasoning_summary="Summarized the document and its extracted fields.",
                cards=[Card(type="document", data={"id": doc.id, "title": doc.title, "type": doc.doc_type, "extracted": ex})],
                evidence=[f"Document {doc.title}: {doc.summary} {ex}"], data_used=[doc.title],
            )
        lines = "\n".join(f"- **{d.title}** ({d.doc_type.replace('_', ' ')}) — {d.summary}" for d in p.documents[:8])
        return self.output(
            answer=f"You have **{len(p.documents)} documents** organized in InsurePilot:\n\n{lines}\n\n"
                   "Upload a new one and I'll classify it, pull out deadlines and amounts, and link it to the right policy.",
            confidence=Confidence.HIGH, reasoning_summary="Listed your indexed documents.",
            data_used=["Document library"], evidence=[lines], suggestions=["Upload a document", "Explain my hospital bill"],
        )
