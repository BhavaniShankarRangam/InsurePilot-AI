from app.ai.agents.base import AgentContext, AgentOutput, BaseAgent, Card, Confidence
from app.ai.llm.base import Task
from app.services.health_benefits import TERMS


def _m(v) -> str:
    return f"${float(v):,.0f}"


class MedicalInsuranceAgent(BaseAgent):
    name = "Medical Insurance Agent"
    description = "Health benefits navigator: costs, EOBs, bills, prior authorization, denials, plain-English terms."
    tools = ("check_procedure_cost", "reconcile_medical_bill", "get_prior_authorization_status", "get_eob", "get_bill",
             "search_policy_documents", "get_provider_network_status")
    escalation_rules = ("Medical necessity questions → licensed clinicians / the health plan",)

    def run(self, ctx: AgentContext) -> AgentOutput:
        low = ctx.lower
        if ctx.portfolio.health_plan is None:
            return self.fallback(ctx, "I don't see a health plan yet. Upload your benefits summary or insurance card.")
        if any(k in low for k in ("can i get", "how much", "cost", "price")) and (ctx.entities.procedure or "mri" in low):
            return self._procedure(ctx)
        if any(k in low for k in ("bill", "eob", "explanation of benefits", "owe", "discrepanc")):
            return self._reconcile(ctx)
        if any(k in low for k in ("authorization", "prior auth", "preauth", "approval for")):
            return self._prior_auth(ctx)
        if "denied" in low or "denial" in low:
            return self._denial(ctx)
        for term, key in (("coinsurance", "coinsurance"), ("copay", "copay"), ("out-of-pocket", "out_of_pocket_max"),
                          ("deductible", "deductible"), ("allowed amount", "allowed_amount")):
            if term in low:
                return self._term(ctx, key)
        if ctx.entities.procedure:
            return self._procedure(ctx)
        return self._overview(ctx)

    def _procedure(self, ctx: AgentContext) -> AgentOutput:
        self.status(ctx, "retrieving", "Identifying your insurance plan")
        self.status(ctx, "tool", "Checking provider network and procedure rules")
        res = self.call(ctx, "check_procedure_cost", procedure=ctx.message, provider_name=ctx.entities.provider or "")
        r = res.data
        hits = self.search(ctx, "prior authorization MRI advanced imaging", category="health", top_k=1)
        net = self.search(ctx, "provider network radiologist in-network", category="health", top_k=1)
        if not r or not r.get("available") or not r.get("provider"):
            return self.output(
                answer=(r or {}).get("summary", "Which hospital or imaging center are you considering?"),
                confidence=Confidence.NEEDS_VERIFICATION, reasoning_summary="Provider couldn't be identified.",
                cards=[Card(type="procedure_check", data=r or {})],
                suggestions=["Lakeside Imaging Center", "St. Brightwater Medical Center"])
        est = r.get("estimate")
        alt = [a for a in r.get("alternatives", []) if a["in_network"] and a["price"] and est and a["price"] < est["negotiated_price"]]
        answer = (
            f"**{r['procedure']} at {r['provider']}**\n\n"
            f"- **Network:** {'✅ In-network' if r['in_network'] else '⚠️ Not listed in your network'} {self.cite(net[0]) if net else ''}\n"
            + (f"- **Estimated cost to you:** about **{_m(est['you_pay'])}** (deductible {_m(est['deductible_portion'])} + "
               f"coinsurance {_m(est['coinsurance_portion'])})\n" if est else "- **Cost:** no price estimate available\n")
            + f"- **Prior authorization:** required for MRI {self.cite(hits[0]) if hits else ''}\n\n"
            + (f"💡 {alt[0]['name']} is in-network and typically costs less ({_m(alt[0]['price'])} vs {_m(est['negotiated_price'])}).\n\n" if alt else "")
            + "Estimates aren't guarantees — the reading radiologist may bill separately, so ask if they're in-network too."
        )
        return self.output(
            answer=answer, task=Task.CROSS_DOCUMENT, policy_specific=True,
            confidence=Confidence.MODERATE,
            reasoning_summary="Matched your plan, the provider's network status, the likely procedure code, your remaining "
                              "deductible and coinsurance, and the plan's authorization rules.",
            cards=[Card(type="procedure_check", data=r)], data_used=["Health plan", "Provider directory (mock)", "Price data (mock)"],
            evidence=[f"Procedure check: {r}"], limitations=r.get("uncertainty", []),
            suggestions=["Check my MRI authorization", "Find an in-network imaging center"],
        )

    def _reconcile(self, ctx: AgentContext) -> AgentOutput:
        self.status(ctx, "retrieving", "Retrieving your hospital bill and EOB")
        self.call(ctx, "get_bill")
        self.call(ctx, "get_eob")
        self.status(ctx, "analyzing", "Comparing bill with insurer EOB")
        r = self.call(ctx, "reconcile_medical_bill").data
        if not r or not r.get("available", True):
            return self.fallback(ctx, "Upload both your hospital bill and the EOB, and I'll compare them.")
        hits = self.search(ctx, "explanation of benefits allowed amount coinsurance patient responsibility", category="health", top_k=2)
        rows = {row["key"]: row["amount"] for row in r["rows"]}
        issues = "\n".join(f"- {'❔' if i['certainty'] == 'possible' else '⚠️'} **{i['title']}** — {i['detail']}" for i in r["issues"])
        cite = " ".join(self.cite(h) for h in hits)
        answer = (
            f"Here's your knee procedure, line by line {cite}:\n\n"
            f"- Hospital charge: **{_m(rows['hospital_charge'])}**\n- Negotiated amount: **{_m(rows['allowed'])}**\n"
            f"- Insurance paid: **{_m(rows['plan_paid'])}**\n- Your deductible: **{_m(rows['deductible'])}**\n"
            f"- Your coinsurance: **{_m(rows['coinsurance'])}**\n- **You owe: {_m(rows['patient_responsibility'])}**\n\n"
            f"{r['summary']}\n\n{issues}"
        )
        return self.output(
            answer=answer, task=Task.CROSS_DOCUMENT, policy_specific=True,
            confidence=Confidence.MODERATE if r["issues"] else Confidence.HIGH,
            reasoning_summary="Compared every amount on the hospital bill with your insurer's EOB and recomputed "
                              "coinsurance from your plan's rate.",
            cards=[Card(type="reconciliation", data=r)], data_used=["Hospital bill", "EOB", "Plan cost-sharing rules"],
            evidence=[f"Reconciliation: {r}"],
            limitations=["Only Bluepeak can confirm whether a processing error occurred."],
            suggestions=["Draft a billing dispute message", "What is coinsurance?", "Should I pay the bill now?"],
        )

    def _prior_auth(self, ctx: AgentContext) -> AgentOutput:
        self.status(ctx, "tool", "Checking prior authorization status")
        auths = self.call(ctx, "get_prior_authorization_status").data or []
        if not auths:
            return self.output(answer="You don't have any prior authorization requests.", confidence=Confidence.HIGH)
        a = auths[0]
        hits = self.search(ctx, "prior authorization clinical documentation decided within days", category="health", top_k=1)
        missing = ", ".join(a["missing"]) or "nothing"
        answer = (
            f"**{a['procedure']}** at {a['provider']} is **{a['status']}** — decision expected by **{a['decision_due']}** "
            f"{self.cite(hits[0]) if hits else ''}.\n\n- **Missing:** {missing}\n"
            f"- **Administrative denial risk:** {a['administrative_risk']}\n\n"
            "I can prepare an authorization packet and a message asking your doctor's office to send the missing records. "
            f"\n\n_{a['disclaimer']}_"
        )
        return self.output(
            answer=answer, confidence=Confidence.MODERATE, policy_specific=True, task=Task.SUMMARY,
            reasoning_summary="Compared submitted documentation with your plan's prior authorization requirements.",
            cards=[Card(type="prior_auth", data=a)], data_used=["Authorization request", "Plan rules"], evidence=[f"Auth: {a}"],
            limitations=["Medical necessity is determined by clinicians and your plan, not InsurePilot."],
            suggestions=["Draft a message to my doctor's office", "How much will the MRI cost?"],
        )

    def _denial(self, ctx: AgentContext) -> AgentOutput:
        denied = [c for c in ctx.portfolio.claims if c.category == "health" and c.status == "denied"]
        hits = self.search(ctx, "claim denied internal appeal 180 days external review", category="health", top_k=1)
        if not denied:
            return self.output(
                answer="None of your health claims are denied right now. If you receive a denial, you can file an internal "
                       f"appeal within 180 days {self.cite(hits[0]) if hits else ''} — I'll help you prepare it.",
                confidence=Confidence.HIGH, reasoning_summary="Checked your health claims and the plan's appeal rules.",
                suggestions=["Explain my EOB", "Check my MRI authorization"])
        return self.fallback(ctx)

    def _term(self, ctx: AgentContext, key: str) -> AgentOutput:
        hp = ctx.portfolio.health_plan
        personal = {
            "deductible": f"Yours is **{_m(hp.deductible_individual)}**, and you've met **{_m(hp.deductible_met)}** this year.",
            "coinsurance": f"Yours is **{hp.coinsurance_in_network}% in-network** and {hp.coinsurance_out_network}% out-of-network.",
            "copay": f"Yours: {', '.join(f'{k.replace('_', ' ')} ${v}' for k, v in hp.copays.items())}.",
            "out_of_pocket_max": f"Yours is **{_m(hp.oop_max_individual)}**; you've spent **{_m(hp.oop_met)}** toward it.",
            "allowed_amount": "Your EOB for the knee procedure shows an allowed amount of $4,300 on an $8,400 charge.",
        }[key]
        hits = self.search(ctx, f"{key.replace('_', ' ')} definition", category="health", top_k=1)
        return self.output(
            answer=f"**In plain English:** {TERMS[key]}\n\n{personal} {self.cite(hits[0]) if hits else ''}",
            confidence=Confidence.HIGH, reasoning_summary="Plain-language definition plus your plan's actual numbers.",
            data_used=["Health plan"], evidence=[TERMS[key], personal], policy_specific=True,
            suggestions=["Explain my EOB", "How much will an MRI cost?"],
        )

    def _overview(self, ctx: AgentContext) -> AgentOutput:
        hp = ctx.portfolio.health_plan
        return self.output(
            answer=f"Your **Bluepeak {hp.plan_type}** at a glance:\n\n"
                   f"- Deductible: {_m(hp.deductible_met)} of {_m(hp.deductible_individual)} met\n"
                   f"- Out-of-pocket: {_m(hp.oop_met)} of {_m(hp.oop_max_individual)}\n"
                   f"- Coinsurance: {hp.coinsurance_in_network}% in-network\n- Network: {hp.network_name}",
            confidence=Confidence.HIGH, reasoning_summary="Read your health plan accumulators.", data_used=["Health plan"],
            evidence=[f"Plan: deductible {hp.deductible_individual}, met {hp.deductible_met}"],
            suggestions=["Can I get an MRI at Lakeside Imaging?", "Explain my hospital bill", "Check my authorization"],
        )


class ProviderNetworkAgent(BaseAgent):
    name = "Provider Network Agent"
    description = "Finds in-network providers and verifies network status."
    tools = ("find_providers", "get_provider_network_status", "search_policy_documents")

    def run(self, ctx: AgentContext) -> AgentOutput:
        if ctx.entities.provider:
            self.status(ctx, "tool", "Checking provider directory")
            st = self.call(ctx, "get_provider_network_status", provider_name=ctx.entities.provider).data or {}
            if st.get("found"):
                return self.output(
                    answer=f"**{st['provider']}** is {'✅ in-network' if st['in_network'] else '⚠️ not listed'} for "
                           f"{st['network']} (checked {st['verified_on']}). " + (st.get("note") or ""),
                    confidence=Confidence.MODERATE, reasoning_summary="Checked the provider directory.",
                    cards=[Card(type="network_status", data=st)], data_used=["Provider directory (mock)"], evidence=[str(st)],
                    limitations=["Directories can be out of date — confirm when booking."])
        self.status(ctx, "tool", "Searching in-network providers")
        query = ctx.message.replace("find", "").replace("in-network", "")
        providers = self.call(ctx, "find_providers", query=query, in_network_only=True).data or []
        hits = self.search(ctx, "provider network directory confirm participation", category="health", top_k=1)
        lines = "\n".join(f"- **{pr['name']}** — {pr['specialty']}, {pr['city']} · ★ {pr['rating']}" for pr in providers[:5])
        return self.output(
            answer=f"In-network options for you:\n\n{lines or '- No matches'}\n\nAlways confirm network status when you book "
                   f"{self.cite(hits[0]) if hits else ''}.",
            confidence=Confidence.MODERATE, reasoning_summary="Searched the provider directory filtered to your network.",
            cards=[Card(type="providers", data={"items": providers})], data_used=["Provider directory (mock)"], evidence=[lines],
            suggestions=["How much is an MRI at Lakeside Imaging?"],
        )
