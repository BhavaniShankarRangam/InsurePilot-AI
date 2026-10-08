from datetime import date

from app.ai.agents.base import AgentContext, AgentOutput, BaseAgent, Card, Confidence
from app.ai.llm.base import Task
from app.services.claims import claim_decision, denial_analysis
from app.services.communication import draft

FNOL_STEPS: list[tuple[str, str]] = [
    ("safety", "First — are you safe, and does anyone need emergency help? If anyone is hurt, call 911 now."),
    ("details", "I'm glad you're okay. What happened, and where? A sentence or two is plenty."),
    ("photos", "Thanks. When it's safe, take photos of all vehicles, the damage, and the scene. You can upload them here "
               "with the camera button. Did you get photos? (yes/no)"),
    ("police", "Was a police report made? If yes, share the report or case number."),
    ("driver", "Do you have the other driver's name, phone, and insurance company? (Type them, or say “skip”.)"),
    ("insurance", "Got it. I'll use your Northstar auto policy. Anything else the insurer should know?"),
]


def _friendly(iso: str) -> str:
    return f"{date.fromisoformat(iso):%B %d}"


class ClaimsAgent(BaseAgent):
    name = "Claims Agent"
    description = "Claim Guardian: FNOL, decision support, status, missing documents, denial analysis, packets."
    tools = ("get_claim", "get_claim_status", "get_policy", "get_coverages", "get_deductible", "search_policy_documents",
             "create_claim_draft", "generate_claim_packet", "send_email", "submit_claim")
    escalation_rules = ("Denied claims with conflicting policy language → offer a licensed professional",
                        "Injuries reported → recommend emergency services first")

    def run(self, ctx: AgentContext) -> AgentOutput:
        low = ctx.lower
        if ctx.memory.get("flow") == "fnol" or any(k in low for k in ("someone hit", "hit my car", "i was in an accident",
                                                                      "i had an accident", "rear-ended me", "crashed")):
            return self._fnol(ctx)
        if ctx.entities.amount and any(k in low for k in ("should i file", "worth filing", "file a claim", "should i claim")):
            return self._decision(ctx)
        if any(k in low for k in ("denied", "denial", "appeal", "why was my claim")) and "health" not in low:
            return self._denial(ctx)
        if any(k in low for k in ("prepare", "start a claim", "new claim", "file my claim")):
            return self._prepare(ctx)
        return self._status(ctx)

    # --- Claim Decision Assistant --------------------------------------
    def _decision(self, ctx: AgentContext) -> AgentOutput:
        category = ctx.entities.category or "auto"
        self.status(ctx, "retrieving", f"Retrieving your {category} deductible")
        self.call(ctx, "get_deductible", category=category, coverage_code="COLL")
        self.status(ctx, "analyzing", "Comparing estimate with deductible")
        d = claim_decision(ctx.portfolio, category, ctx.entities.amount or 0)
        if not d["available"]:
            return self.fallback(ctx, d["message"])
        hits = self.search(ctx, "collision deductible premium renewal claim", category=category, top_k=1)
        cite = self.cite(hits[0]) if hits else ""
        answer = (
            f"Here's the math {cite}:\n\n- **Repair estimate:** ${d['repair_estimate']:,.0f}\n"
            f"- **Your collision deductible:** ${d['deductible']:,.0f}\n"
            f"- **Insurer might pay:** about **${d['estimated_insurer_payment']:,.0f}**\n"
            f"- **Claims in the last 3 years:** {d['prior_claims']}\n\n"
            "Filing could get you that payment, but if you were at fault it may affect your premium at renewal. "
            "Paying yourself keeps your record clean. **This is your call** — I've laid out both options below."
        )
        return self.output(
            answer=answer, task=Task.CLAIMS_REASONING, confidence=Confidence.HIGH if hits else Confidence.MODERATE,
            policy_specific=True,
            reasoning_summary="Subtracted your collision deductible from the estimate and checked your claim history and "
                              "the policy's renewal language. No recommendation is made.",
            cards=[Card(type="claim_decision", data=d)], data_used=["Collision deductible", "Claim history"],
            evidence=[f"Decision data: {d}"],
            limitations=["The adjuster's assessment may differ from the shop estimate.",
                         "Exact premium impact can't be known in advance."],
            suggestions=["Was the other driver at fault?", "Start a claim anyway", "How does rental coverage work?"],
        )

    # --- Denial analysis ---------------------------------------------------
    def _denial(self, ctx: AgentContext) -> AgentOutput:
        p = ctx.portfolio
        claim = (p.claim_by_ref(ctx.entities.claim_ref) if ctx.entities.claim_ref else None) or next(
            (c for c in p.claims if c.status == "denied"), None)
        if claim is None:
            return self.output(answer="None of your claims are denied right now. ✅", confidence=Confidence.HIGH,
                               reasoning_summary="Checked the status of all your claims.")
        self.status(ctx, "retrieving", "Reading the denial letter")
        self.call(ctx, "get_claim", claim_ref=claim.id)
        self.status(ctx, "analyzing", "Checking exclusions and endorsements")
        excl = self.search(ctx, "water exclusion backs up through sewers or drains", category=claim.category, top_k=1)
        endo = self.search(ctx, "water backup endorsement sump overflow limit", category=claim.category, top_k=1)
        a = denial_analysis(p, claim)
        e_cite = self.cite(excl[0]) if excl else ""
        n_cite = self.cite(endo[0]) if endo else ""
        has_endorsement = any(f["kind"] == "endorsement" for f in a["findings"])
        answer = (
            f"**Denial reason:** {a['denial_reason']} {e_cite}\n\n"
            + (f"**What I found:** Your policy also has a **water-backup endorsement** with a **$10,000 limit** {n_cite}.\n\n"
               "The main policy contains a water exclusion, but your policy also contains a water-backup endorsement. "
               "**Whether it applies depends on the actual cause of loss** — your claim notes say water came up through "
               "the floor drain, which is what the endorsement describes.\n\n" if has_endorsement else "")
            + (f"You have until **{date.fromisoformat(a['deadline']['due']):%B %d}** to request reconsideration. I can generate questions for the "
               "adjuster, prepare an evidence package, draft an appeal, or connect you with a licensed professional."
               if a.get("deadline") else "")
        )
        q = draft(p, "adjuster_questions", claim=claim)
        return self.output(
            answer=answer, task=Task.CROSS_DOCUMENT,
            confidence=Confidence.MODERATE if has_endorsement else Confidence.HIGH, policy_specific=True,
            reasoning_summary="Compared the denial letter against your policy's exclusions and endorsements.",
            cards=[Card(type="denial_analysis", data=a), Card(type="draft", data=q)],
            data_used=["Denial letter", "Home policy exclusions", "Endorsement HO-WB"], evidence=[f"Analysis: {a}"],
            limitations=["Only the insurer (or an appraiser/court) can decide whether the endorsement applies."],
            suggestions=["Prepare an appeal draft", "Prepare evidence package", "Talk to a licensed professional"],
            escalate=has_endorsement,
        )

    # --- Status / timeline ------------------------------------------------
    def _status(self, ctx: AgentContext) -> AgentOutput:
        p = ctx.portfolio
        claim = (p.claim_by_ref(ctx.entities.claim_ref) if ctx.entities.claim_ref else None) or (
            p.claim_by_ref(ctx.page["claim_id"]) if ctx.page.get("claim_id") else None) or (p.open_claims[0] if p.open_claims else None)
        if claim is None:
            return self.output(answer="You don't have any open claims — that's a good thing. 🎉", confidence=Confidence.HIGH,
                               reasoning_summary="Checked all claims.", suggestions=["Start a new claim"])
        self.status(ctx, "tool", "Checking claim status with your insurer")
        st = self.call(ctx, "get_claim_status", claim_ref=claim.id).data or {}
        detail = self.call(ctx, "get_claim", claim_ref=claim.id).data
        current = next((e for e in claim.events if e.status == "current"), None)
        nxt = next((e for e in claim.events if e.status == "upcoming"), None)
        missing = claim.missing_documents
        answer = (
            f"**Claim {claim.claim_number} · {claim.title}** is **{claim.status.replace('_', ' ')}**.\n\n"
            f"- **Where it is now:** {current.title if current else claim.stage}\n"
            + (f"- **What's next:** {nxt.title}\n" if nxt else "")
            + (f"- **Adjuster:** {st.get('adjuster')}\n" if st.get("adjuster") else "")
            + (f"\n⚠️ Your adjuster still needs: **{', '.join(missing)}**. "
               f"Deadline: {_friendly(claim.deadlines[0]['due']) if claim.deadlines else 'as soon as possible'}." if missing else "")
        )
        return self.output(
            answer=answer, confidence=Confidence.HIGH, task=Task.SUMMARY,
            reasoning_summary="Retrieved live status from your carrier and your claim timeline.",
            cards=[Card(type="claim_timeline", data=detail)], data_used=["Carrier claim status", "Claim timeline"],
            evidence=[f"Claim: {detail}"],
            suggestions=["Prepare my claim", "Draft an email to my adjuster", "Do I need to file this claim?"],
        )

    # --- Prepare claim / packet --------------------------------------------
    def _prepare(self, ctx: AgentContext) -> AgentOutput:
        p = ctx.portfolio
        claim = (p.claim_by_ref(ctx.entities.claim_ref) if ctx.entities.claim_ref else None) or (
            p.open_claims[0] if p.open_claims else None)
        if claim is None:
            ctx.memory["flow"] = "fnol"
            ctx.memory["fnol"] = {"step": 0, "answers": {}}
            return self._fnol(ctx, start=True)
        self.status(ctx, "tool", "Assembling your claim packet")
        packet = self.call(ctx, "generate_claim_packet", claim_ref=claim.id).data
        actions: list[str] = []
        if claim.missing_documents and claim.adjuster_email:
            msg = draft(p, "claim_email", claim=claim)
            res = self.call(ctx, "send_email", to=msg["to"], subject=msg["subject"], body=msg["body"])
            if res.pending_action_id:
                actions.append(res.pending_action_id)
        answer = (
            f"I've prepared the packet for **claim {claim.claim_number}**:\n\n"
            f"- **Included:** {', '.join(packet['documents_included']) or 'none yet'}\n"
            f"- **Still missing:** {', '.join(packet['documents_missing']) or 'nothing'}\n\n"
            + ("I drafted an email to your adjuster about the missing item. **It won't be sent until you approve it.**"
               if actions else "Everything looks complete.")
        )
        return self.output(
            answer=answer, confidence=Confidence.HIGH, reasoning_summary="Assembled documents and timeline into a packet.",
            cards=[Card(type="claim_packet", data=packet)], action_ids=actions, data_used=["Claim documents", "Timeline"],
            evidence=[f"Packet: {packet}"], suggestions=["Upload the police report", "Show the claim timeline"],
        )

    # --- Guided FNOL (voice-friendly) --------------------------------------
    def _fnol(self, ctx: AgentContext, start: bool = False) -> AgentOutput:
        state = ctx.memory.get("fnol")
        if ctx.memory.get("flow") != "fnol" or state is None:
            ctx.memory["flow"] = "fnol"
            state = ctx.memory["fnol"] = {"step": 0, "answers": {"initial": ctx.message}}
            return self._fnol_prompt(ctx, 0)
        step = state["step"]
        key = FNOL_STEPS[step][0]
        state["answers"][key] = ctx.message
        low = ctx.lower
        if key == "safety" and any(w in low for w in ("hurt", "injur", "bleeding", "ambulance", "not safe", "no i'm not")):
            return self.output(
                answer="**Please call 911 now** if anyone is injured or in danger. Your safety matters more than the claim. "
                       "I'll be right here when you're ready to continue.",
                confidence=Confidence.HUMAN_REVIEW, reasoning_summary="Injury indicated — emergency services first.",
                cards=[Card(type="emergency", data={"call": "911"})], escalate=True,
            )
        step += 1
        state["step"] = step
        if step < len(FNOL_STEPS):
            return self._fnol_prompt(ctx, step)

        answers = state["answers"]
        description = " ".join(v for k, v in answers.items() if k in ("initial", "details", "insurance") and v)
        self.status(ctx, "tool", "Creating your claim draft")
        res = self.call(ctx, "create_claim_draft", category="auto", title="Auto accident — reported with InsurePilot",
                        description=description[:900])
        ctx.memory.pop("flow", None)
        ctx.memory.pop("fnol", None)
        claim_ref = res.data["claim_id"] if res.ok else None
        actions: list[str] = []
        if claim_ref:
            sub = self.call(ctx, "submit_claim", claim_ref=claim_ref)
            if sub.pending_action_id:
                actions.append(sub.pending_action_id)
        return self.output(
            answer="Thank you — I've prepared your **claim draft** with everything you told me. Your collision deductible is "
                   "$1,000, and rental reimbursement (up to $40/day) may help while your car is repaired.\n\n"
                   "**Review it below. It won't be submitted until you approve.**",
            confidence=Confidence.HIGH, task=Task.CLAIMS_REASONING,
            reasoning_summary="Collected incident details step by step and created a draft linked to your auto policy.",
            cards=[Card(type="fnol_summary", data={"answers": answers, "claim_id": claim_ref})], action_ids=actions,
            data_used=["Your answers", "Auto policy"], evidence=[f"FNOL answers: {answers}"],
            suggestions=["Upload accident photos", "Do I need to file this claim?"],
        )

    def _fnol_prompt(self, ctx: AgentContext, step: int) -> AgentOutput:
        return self.output(
            answer=FNOL_STEPS[step][1], confidence=Confidence.HIGH, task=Task.SUMMARY,
            reasoning_summary="Guided accident reporting (first notice of loss).",
            cards=[Card(type="guided_flow", data={"flow": "fnol", "step": step, "total": len(FNOL_STEPS),
                                                  "steps": ["Safety", "Incident details", "Photos", "Police information",
                                                            "Driver details", "Insurance information", "Claim preparation"]})],
            suggestions=["Yes, everyone is safe", "Someone is hurt"] if step == 0 else ["Skip"],
        )
