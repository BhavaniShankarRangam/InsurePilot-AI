"""Intent + entity understanding. Rule-based (deterministic, offline) with optional LLM refinement."""

import re

from app.ai.agents.base import Entities

CATEGORY_TERMS: dict[str, tuple[str, ...]] = {
    "auto": ("car", "auto", "vehicle", "driving", "driver", "collision", "rav4", "crash", "hit my", "fender", "bumper"),
    "home": ("home", "house", "roof", "basement", "dwelling", "water damage", "rebuild", "flood", "homeowner"),
    "health": ("health", "medical", "mri", "doctor", "hospital", "eob", "copay", "coinsurance", "prior auth",
               "authorization", "procedure", "bill", "surgery", "knee", "deductible remaining", "out-of-pocket"),
    "life": ("life insurance", "life policy", "beneficiar", "death benefit", "term life"),
    "pet": ("pet", "dog", "cat", "vet", "miso"),
    "travel": ("travel", "trip", "flight", "vacation"),
    "renters": ("renter", "apartment", "lease"),
    "commercial": ("business", "commercial", "company"),
}

AGENT_TERMS: dict[str, tuple[str, ...]] = {
    "Human Escalation Agent": ("talk to a human", "real person", "speak to someone", "human agent", "licensed agent",
                               "escalate", "talk to an agent", "advisor"),
    "Fraud Signal Agent": ("scam", "suspicious", "fraud", "legit", "phishing", "gift card", "wire money"),
    "Communication Agent": ("draft", "write an email", "write a letter", "email my", "message to", "compose", "appeal letter",
                            "questions for the adjuster", "questions for adjuster", "dispute letter"),
    "Claims Agent": ("claim", "accident", "hit my car", "someone hit", "file", "adjuster", "denied", "denial", "repair",
                     "fnol", "crash", "damage", "rear-ended", "appeal"),
    "Medical Insurance Agent": ("mri", "eob", "medical bill", "hospital bill", "copay", "coinsurance", "prior auth",
                                "authorization", "procedure", "health claim", "explain my bill", "explain bill", "ct scan",
                                "deductible remaining", "out-of-pocket"),
    "Provider Network Agent": ("in-network", "in network", "find a doctor", "find provider", "find a provider", "specialist",
                               "orthopedic", "imaging center", "provider"),
    "Renewal Agent": ("renew", "premium increase", "premium increased", "why did my premium", "price went up",
                      "more expensive", "rate increase", "premium go up", "premium went up"),
    "Insurance Shopping Agent": ("compare", "quote", "shop", "equivalent", "switch carrier", "cheaper", "alternatives"),
    "Risk Agent": ("gap", "gaps", "risk", "what needs attention", "health score", "underinsured", "am i protected",
                   "anything wrong", "handle my insurance"),
    "Billing Agent": ("payment", "pay my", "billing", "autopay", "due date", "when is my bill", "invoice"),
    "Document Intelligence Agent": ("document", "upload", "summarize", "this pdf", "what does this say", "my files"),
    "Coverage Agent": ("covered", "cover ", "coverage for", "does my policy", "am i covered", "is it covered", "exclusion",
                       "endorsement", "limit"),
    "Policy Intelligence Agent": ("explain", "deductible", "policy", "what is", "summary", "overview", "show my"),
}

# Higher priority wins ties; specific agents beat generic ones.
PRIORITY = [
    "Human Escalation Agent", "Fraud Signal Agent", "Communication Agent", "Medical Insurance Agent", "Renewal Agent",
    "Claims Agent", "Provider Network Agent", "Insurance Shopping Agent", "Risk Agent", "Coverage Agent", "Billing Agent",
    "Document Intelligence Agent", "Policy Intelligence Agent",
]

PAGE_AGENT = {"claims": "Claims Agent", "health": "Medical Insurance Agent", "policies": "Policy Intelligence Agent",
              "compare": "Insurance Shopping Agent", "documents": "Document Intelligence Agent", "wallet": "Policy Intelligence Agent"}

AMOUNT = re.compile(r"\$\s?(\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{2})?")
CLAIM_REF = re.compile(r"\b(MED-\d{5}|\d{5})\b", re.IGNORECASE)


def extract_entities(text: str, page: dict) -> Entities:
    lower = text.lower()
    cats = [c for c, terms in CATEGORY_TERMS.items() if any(t in lower for t in terms)]
    amount = None
    if m := AMOUNT.search(text):
        amount = float(m.group(1).replace(",", ""))
    claim = CLAIM_REF.search(text)
    provider = None
    if m := re.search(r"\bat ([A-Z][\w.&' -]{2,60}?)(?:[?.!,]|$)", text):
        provider = m.group(1).strip()
    procedure = next((p for p in ("mri", "ct scan", "x-ray", "arthroscopy", "surgery") if p in lower), None)
    category = cats[0] if cats else page.get("category")
    return Entities(category=category, categories=cats, claim_ref=claim.group(1).upper() if claim else None,
                    amount=amount, provider=provider, procedure=procedure)


def classify_intent(text: str, page: dict, memory: dict) -> tuple[str, float]:
    """Returns (agent_name, score). Score 0 means no keyword evidence (page/memory fallback used)."""
    lower = f" {text.lower()} "
    if memory.get("flow") == "fnol":
        return "Claims Agent", 1.0
    scores: dict[str, float] = {}
    for agent, terms in AGENT_TERMS.items():
        s = sum(len(t.split()) for t in terms if t in lower)
        if s:
            scores[agent] = s
    if re.search(r"\b(covered|cover|coverage for)\b", lower) and not re.search(r"\b(file|denied|status|filed)\b", lower):
        scores["Coverage Agent"] = scores.get("Coverage Agent", 0) + 2
    if not scores:
        return PAGE_AGENT.get(page.get("section", ""), "Policy Intelligence Agent"), 0.0
    best = max(scores.values())
    for agent in PRIORITY:
        if scores.get(agent, 0) >= best:
            return agent, best
    return "Policy Intelligence Agent", 0.0
