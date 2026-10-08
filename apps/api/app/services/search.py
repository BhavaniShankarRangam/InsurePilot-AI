"""Global smart search across policies, claims, documents, benefits, providers, bills and messages."""

from sqlalchemy.orm import Session

from app.rag.retriever import HybridRetriever, RetrievalFilters
from app.rag.text import tokenize
from app.services.portfolio import load_portfolio


def _hit(q: set[str], text: str) -> float:
    toks = set(tokenize(text))
    return len(q & toks) / max(1, len(q))


def global_search(db: Session, user_id: str, query: str, limit: int = 20) -> list[dict]:
    p = load_portfolio(db, user_id)
    q = set(tokenize(query))
    raw = query.strip().lower()
    results: list[dict] = []

    for pol in p.policies:
        text = f"{pol.category} {pol.product_name} {pol.carrier.name} {pol.summary} " + " ".join(
            f"{c.name} {c.plain_language}" for c in pol.coverages)
        s = _hit(q, text) + (1 if raw in pol.category else 0)
        if s > 0:
            results.append({"type": "policy", "id": pol.id, "title": f"{pol.carrier.short_name} {pol.product_name}",
                            "subtitle": pol.summary, "link": f"/policies/{pol.id}", "score": s})
    for c in p.claims:
        s = _hit(q, f"claim {c.title} {c.description} {c.status}") + (2 if raw.replace("claim", "").strip() == c.claim_number.lower() else 0)
        if s > 0:
            results.append({"type": "claim", "id": c.id, "title": f"Claim {c.claim_number} · {c.title}",
                            "subtitle": c.status.replace("_", " ").title(), "link": f"/claims/{c.id}", "score": s})
    for pr in p.providers.values():
        s = _hit(q, f"{pr.name} {pr.specialty} {pr.kind} provider doctor")
        if s > 0:
            results.append({"type": "provider", "id": pr.id, "title": pr.name, "subtitle": f"{pr.specialty} · {pr.city}",
                            "link": "/health?tab=providers", "score": s * 0.8})
    for b in p.bills:
        s = _hit(q, f"bill medical {b.service_description}")
        if s > 0:
            results.append({"type": "bill", "id": b.id, "title": b.service_description, "subtitle": f"${float(b.amount_due):,.0f} due",
                            "link": "/health?tab=bills", "score": s})
    if p.health_plan:
        for ben in p.health_plan.benefits:
            s = _hit(q, f"benefit {ben['name']} {ben['coverage']}")
            if s > 0:
                results.append({"type": "benefit", "id": ben["name"], "title": ben["name"], "subtitle": ben["coverage"],
                                "link": "/health", "score": s})
    for n in p.notifications:
        s = _hit(q, f"{n.title} {n.body}")
        if s > 0:
            results.append({"type": "message", "id": n.id, "title": n.title, "subtitle": n.body, "link": n.link or "/dashboard",
                            "score": s * 0.7})
    for r in HybridRetriever(db).search(query, RetrievalFilters(user_id=user_id), top_k=5, min_score=0.2):
        results.append({"type": "document", "id": r.document.id, "title": r.citation().label, "subtitle": r.compressed[:160],
                        "link": f"/documents?doc={r.document.id}", "score": r.score * 1.5})
    results.sort(key=lambda r: -r["score"])
    seen: set[tuple[str, str]] = set()
    unique = []
    for r in results:
        key = (r["type"], r["title"])
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique[:limit]
