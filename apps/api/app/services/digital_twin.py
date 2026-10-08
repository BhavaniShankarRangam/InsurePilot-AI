"""Insurance Digital Twin: knowledge-graph projection of a user's insurance world."""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import GraphEdge
from app.services.portfolio import load_portfolio


def rebuild_graph(db: Session, user_id: str) -> int:
    p = load_portfolio(db, user_id)
    db.execute(delete(GraphEdge).where(GraphEdge.user_id == user_id))
    edges: list[GraphEdge] = []

    def edge(st: str, sid: str, pred: str, ot: str, oid: str) -> None:
        edges.append(GraphEdge(user_id=user_id, subject_type=st, subject_id=sid, predicate=pred, object_type=ot, object_id=oid))

    for a in p.assets:
        edge("user", user_id, "owns", a.kind, a.id)
    for pol in p.policies:
        if pol.asset_id:
            edge(next((a.kind for a in p.assets if a.id == pol.asset_id), "asset"), pol.asset_id, "insured_by", "policy", pol.id)
        else:
            edge("user", user_id, "covered_by", "policy", pol.id)
        edge("policy", pol.id, "issued_by", "carrier", pol.carrier_id)
        for cov in pol.coverages:
            edge("policy", pol.id, "includes", "coverage", cov.id)
        for end in pol.endorsements:
            edge("policy", pol.id, "modified_by", "endorsement", end.id)
    for c in p.claims:
        edge("claim", c.id, "belongs_to", "policy", c.policy_id)
    for doc in p.documents:
        if doc.claim_id:
            edge("document", doc.id, "supports", "claim", doc.claim_id)
        elif doc.policy_id:
            edge("document", doc.id, "describes", "policy", doc.policy_id)
    if p.health_plan:
        for prov in p.providers.values():
            if p.health_plan.network_name in (prov.networks or []):
                edge("provider", prov.id, "participates_in", "network", p.health_plan.network_name)
    for auth in p.authorizations:
        edge("authorization", auth.id, "requested_under", "policy", auth.policy_id)
    db.add_all(edges)
    db.flush()
    return len(edges)


CATEGORY_LABEL = {
    "auto": "Car", "home": "Home", "renters": "Renters", "health": "Health", "life": "Life",
    "travel": "Travel", "pet": "Pet", "commercial": "Business",
}


def graph_view(db: Session, user_id: str) -> dict:
    """Nodes + links for the 3D Insurance Universe and Digital Twin views."""
    p = load_portfolio(db, user_id)
    nodes: list[dict] = [{"id": user_id, "type": "user", "label": p.user.preferred_name or p.user.full_name, "status": "ok"}]
    links: list[dict] = []
    from app.services.health_score import policy_alerts

    for pol in p.policies:
        alerts = policy_alerts(p, pol)
        status = "attention" if any(a["severity"] == "attention" for a in alerts) else "review" if alerts else "ok"
        if pol.status == "lapsed":
            status = "inactive"
        cat_id = f"cat-{pol.category}"
        nodes.append({
            "id": cat_id, "type": "category", "category": pol.category, "label": CATEGORY_LABEL.get(pol.category, pol.category),
            "status": status, "summary": pol.summary, "alerts": [a["title"] for a in alerts],
            "premium": float(pol.premium_annual), "carrier": pol.carrier.name, "link": f"/policies/{pol.id}",
        })
        links.append({"source": user_id, "target": cat_id, "kind": "owns"})
        nodes.append({"id": pol.id, "type": "policy", "category": pol.category, "label": f"{pol.carrier.short_name} {pol.product_name}",
                      "status": status, "link": f"/policies/{pol.id}"})
        links.append({"source": cat_id, "target": pol.id, "kind": "insured_by"})
        carrier_id = f"carrier-{pol.carrier_id}"
        if not any(n["id"] == carrier_id for n in nodes):
            nodes.append({"id": carrier_id, "type": "carrier", "label": pol.carrier.name, "status": "ok"})
        links.append({"source": pol.id, "target": carrier_id, "kind": "issued_by"})
    for c in p.claims:
        cs = "attention" if c.status in ("denied",) or c.missing_documents else "ok"
        nodes.append({"id": c.id, "type": "claim", "category": c.category, "label": f"Claim {c.claim_number}",
                      "status": cs, "summary": c.title, "link": f"/claims/{c.id}"})
        links.append({"source": c.policy_id, "target": c.id, "kind": "has_claim"})
    if p.health_plan:
        hp_policy = p.policy_by_id(p.health_plan.policy_id)
        for prov in p.providers.values():
            if prov.id in {e.provider_id for e in p.eobs} | {a.provider_id for a in p.authorizations}:
                in_net = p.health_plan.network_name in (prov.networks or [])
                nodes.append({"id": prov.id, "type": "provider", "label": prov.name,
                              "status": "ok" if in_net else "review", "summary": "In-network" if in_net else "Not in directory"})
                if hp_policy:
                    links.append({"source": hp_policy.id, "target": prov.id, "kind": "provider"})
    return {"nodes": nodes, "links": links}
