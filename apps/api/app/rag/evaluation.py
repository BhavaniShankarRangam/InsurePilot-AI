"""RAG + agent evaluation: retrieval quality, faithfulness, citation accuracy, latency and cost.

Custom metrics run offline. If `ragas` is installed and a live LLM is configured, RAGAS
metrics can be layered on top of the same cases (see `run_ragas`).
"""

import re
import time
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.agents import get_agent
from app.ai.agents.base import AgentContext
from app.ai.agents.intent import classify_intent, extract_entities
from app.db.models import EvaluationRun, LLMUsage
from app.rag.retriever import HybridRetriever, RetrievalFilters
from app.rag.text import tokenize
from app.services.portfolio import load_portfolio


@dataclass
class EvalCase:
    question: str
    expected_sections: list[str]  # substrings of citation labels considered relevant
    expected_facts: list[str]  # facts that must appear in the answer
    expected_agent: str


GOLDEN: list[EvalCase] = [
    EvalCase("What is my collision deductible?", ["Collision Coverage", "Declarations"], ["$1,000"], "Policy Intelligence Agent"),
    EvalCase("Is water backup covered on my home policy?", ["HO-WB", "Exclusions"], ["$10,000"], "Coverage Agent"),
    EvalCase("Why was my home claim denied?", ["Exclusions", "HO-WB", "Claim Determination"], ["$10,000", "water"], "Claims Agent"),
    EvalCase("Why did my premium increase?", ["Renewal Notice"], ["$1,610", "$1,916"], "Renewal Agent"),
    EvalCase("Can I get an MRI at Lakeside Imaging?", ["Prior Authorization", "Provider Network"], ["In-network"], "Medical Insurance Agent"),
    EvalCase("Explain my hospital bill", ["Explanation of Benefits", "Cost Sharing"], ["$2,760", "$4,300"], "Medical Insurance Agent"),
    EvalCase("My car repair is $1,200. Should I file a claim?", ["Collision Coverage"], ["$200", "$1,000"], "Claims Agent"),
    EvalCase("Who is the beneficiary on my life insurance?", ["Beneficiaries", "Policy Schedule"], [], "Policy Intelligence Agent"),
]

_MONEY = re.compile(r"\$[\d,]+(?:\.\d{2})?")


_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _numbers(text: str) -> set[float]:
    return {round(float(n.replace(",", "")), 2) for n in _NUMBER.findall(text)}


def _faithfulness(answer: str, evidence: str) -> float:
    """Share of monetary figures in the answer that are supported (numerically) by the evidence."""
    figures = {round(float(f[1:].replace(",", "")), 2) for f in _MONEY.findall(answer)}
    if not figures:
        return 1.0
    return len(figures & _numbers(evidence)) / len(figures)


def _relevance(question: str, answer: str) -> float:
    q = set(tokenize(question))
    return len(q & set(tokenize(answer))) / max(1, len(q))


def run_evaluation(db: Session, user_id: str, suite: str = "golden-v1") -> EvaluationRun:
    portfolio = load_portfolio(db, user_id)
    retriever = HybridRetriever(db)
    cost_before = db.scalar(select(func.coalesce(func.sum(LLMUsage.cost_usd), 0.0))) or 0.0
    cases: list[dict] = []
    for case in GOLDEN:
        t0 = time.perf_counter()
        hits = retriever.search(case.question, RetrievalFilters(user_id=user_id), top_k=4)
        labels = [h.citation().label for h in hits]
        relevant = [lbl for lbl in labels if any(s.lower() in lbl.lower() for s in case.expected_sections)]
        precision = len(relevant) / len(labels) if labels else 0.0
        recall = (sum(1 for s in case.expected_sections if any(s.lower() in lbl.lower() for lbl in labels))
                  / len(case.expected_sections)) if case.expected_sections else 1.0
        context_relevance = sum(_relevance(case.question, h.chunk.content) for h in hits) / len(hits) if hits else 0.0

        agent_name, _ = classify_intent(case.question, {}, {})
        ctx = AgentContext(db=db, user_id=user_id, conversation_id=None, message=case.question, history=[], page={},
                           portfolio=portfolio, entities=extract_entities(case.question, {}), memory={})
        out = get_agent(agent_name).safe_run(ctx)
        evidence = "\n".join(out.evidence)
        facts_found = sum(1 for f in case.expected_facts if f.lower() in out.answer.lower())
        cited = [c["label"] for c in out.citations]
        citation_accuracy = (sum(1 for c in cited if any(s.lower() in c.lower() for s in case.expected_sections)) / len(cited)
                             ) if cited else (1.0 if not case.expected_sections else 0.0)
        faith = _faithfulness(out.answer, evidence)
        cases.append({
            "question": case.question,
            "agent": agent_name,
            "routing_correct": agent_name == case.expected_agent,
            "retrieved": labels,
            "context_precision": round(precision, 3),
            "context_recall": round(recall, 3),
            "context_relevance": round(context_relevance, 3),
            "faithfulness": round(faith, 3),
            "answer_relevance": round(_relevance(case.question, out.answer), 3),
            "fact_coverage": round(facts_found / len(case.expected_facts), 3) if case.expected_facts else 1.0,
            "citation_accuracy": round(citation_accuracy, 3),
            "hallucination_risk": round(1 - faith, 3),
            "confidence": out.confidence,
            "latency_ms": int((time.perf_counter() - t0) * 1000),
        })
    db.rollback()  # discard tool-execution side effects from evaluation runs
    keys = ["context_precision", "context_recall", "context_relevance", "faithfulness", "answer_relevance", "fact_coverage",
            "citation_accuracy", "hallucination_risk", "latency_ms"]
    metrics = {k: round(sum(c[k] for c in cases) / len(cases), 3) for k in keys}
    metrics["routing_accuracy"] = round(sum(c["routing_correct"] for c in cases) / len(cases), 3)
    cost_after = db.scalar(select(func.coalesce(func.sum(LLMUsage.cost_usd), 0.0))) or 0.0
    metrics["cost_usd"] = round(float(cost_after) - float(cost_before), 6)
    metrics["cases"] = len(cases)
    run = EvaluationRun(suite=suite, metrics=metrics, cases=cases,
                        notes="Custom offline metrics. Enable RAGAS with a live LLM for model-graded faithfulness.")
    db.add(run)
    db.commit()
    return run


def run_ragas(cases: list[dict]) -> dict | None:  # pragma: no cover - optional dependency
    try:
        import ragas  # noqa: F401
    except ImportError:
        return None
    return {"status": "ragas available — wire your LLM/embeddings wrappers here"}
