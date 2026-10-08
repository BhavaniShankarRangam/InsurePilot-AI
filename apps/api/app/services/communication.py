"""Editable communication drafts. Nothing is sent without explicit approval (see AIAction)."""

from app.db.models import Claim, Policy
from app.services.portfolio import Portfolio

DRAFT_KINDS = ("claim_email", "adjuster_questions", "appeal", "billing_dispute", "provider_inquiry", "renewal_inquiry",
               "policy_clarification")


def draft(p: Portfolio, kind: str, claim: Claim | None = None, policy: Policy | None = None) -> dict:
    name = p.user.full_name
    if kind == "adjuster_questions" and claim:
        body = (f"Hi {claim.adjuster_name or 'there'},\n\nThank you for reviewing claim {claim.claim_number}. "
                "I have a few questions to make sure I understand the decision:\n\n"
                "1. What was determined to be the cause of loss, and what evidence supports that?\n"
                "2. Was the Water Backup and Sump Overflow endorsement (HO-WB) considered in the review?\n"
                "3. If the water entered through the floor drain, would the endorsement's $10,000 limit apply?\n"
                "4. What additional documentation would help you reconsider?\n\n"
                f"Thank you,\n{name}")
        return {"kind": kind, "to": claim.adjuster_email, "subject": f"Questions about claim {claim.claim_number}", "body": body}
    if kind == "appeal" and claim:
        body = (f"To the Claims Review Team,\n\nI am requesting reconsideration of claim {claim.claim_number} "
                f"(date of loss {claim.incident_date:%B %d, %Y}), which was denied under the water exclusion.\n\n"
                "My policy includes Endorsement HO-WB — Water Backup and Sump Discharge or Overflow — which covers up to "
                "$10,000 for water that backs up through sewers or drains (Home Policy, page 31). The water in my basement "
                "entered through the floor drain during a storm, which appears to fall within this endorsement.\n\n"
                "I am attaching photos of the drain area and [a plumber's report on the cause of loss]. Please review the "
                "claim under the endorsement and let me know the outcome in writing.\n\n"
                f"Sincerely,\n{name}")
        return {"kind": kind, "to": claim.adjuster_email, "subject": f"Request for reconsideration — claim {claim.claim_number}", "body": body}
    if kind == "claim_email" and claim:
        body = (f"Hi {claim.adjuster_name or 'there'},\n\nAttached is the {', '.join(claim.missing_documents) or 'requested document'} "
                f"for claim {claim.claim_number}. Please let me know if anything else is needed to finish processing.\n\n"
                f"Thanks,\n{name}")
        return {"kind": kind, "to": claim.adjuster_email, "subject": f"Claim {claim.claim_number} — requested documents", "body": body}
    if kind == "billing_dispute":
        body = ("Hello Bluepeak Member Services,\n\nI'm reviewing the EOB for claim MED-55821 (knee arthroscopy at "
                "St. Brightwater Medical Center). The coinsurance shown is $760, but at my plan's 20% in-network rate I "
                "expected about $460. The anesthesia provider may have been processed as out-of-network even though the "
                "facility is in-network.\n\nCould you please review whether any line was processed at the out-of-network "
                "rate and whether No Surprises Act protections apply?\n\n"
                f"Thank you,\n{name}")
        return {"kind": kind, "to": "memberservices@bluepeak.example", "subject": "Question about EOB for claim MED-55821", "body": body}
    if kind == "renewal_inquiry" and policy:
        body = (f"Hello {policy.carrier.name},\n\nMy {policy.product_name} policy renews soon with a premium increase from "
                f"${float(policy.prior_premium_annual or 0):,.0f} to ${float(policy.premium_annual):,.0f}. Could you confirm "
                "which discounts I'm eligible for (safe-driver, paperless, multi-policy) and whether any rating factors can be "
                f"re-reviewed?\n\nThank you,\n{name}")
        return {"kind": kind, "to": policy.carrier.claims_email, "subject": "Questions about my renewal premium", "body": body}
    if kind == "provider_inquiry":
        body = ("Hello,\n\nBefore scheduling, could you confirm that your facility and the reading radiologist are "
                "in-network with Bluepeak Choice PPO, and share the estimated cost for CPT 72148?\n\n"
                f"Thank you,\n{name}")
        return {"kind": kind, "to": "scheduling@lakesideimaging.example", "subject": "Network and cost question", "body": body}
    target = policy.carrier.name if policy else "my insurer"
    return {"kind": "policy_clarification", "to": policy.carrier.claims_email if policy else "",
            "subject": "Question about my policy",
            "body": f"Hello {target},\n\nCould you help me understand [your question]?\n\nThank you,\n{name}"}
