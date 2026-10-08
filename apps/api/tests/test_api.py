import json


def test_healthz(client):
    assert client.get("/healthz").json()["status"] == "ok"


def test_requires_auth(client):
    client.cookies.clear()
    assert client.get("/dashboard").status_code == 401


def test_demo_login_and_me(authed):
    me = authed.get("/auth/me").json()
    assert me["email"] == "demo@insurepilot.ai"
    assert "ai:approve_actions" in me["permissions"]


def test_csrf_header_required_for_cookie_mutations(authed):
    r = authed.post("/notifications/read-all", headers={"X-InsurePilot-Client": ""})
    assert r.status_code == 403


def test_dashboard(authed):
    d = authed.get("/dashboard").json()
    assert d["name"] == "Alex"
    assert d["stats"]["active_claims"] >= 1
    assert d["layout"][0] == "claims"
    assert {p["category"] for p in d["policies"]} >= {"auto", "home", "health", "life"}
    assert all("•" in p["policy_number"] for p in d["policies"])  # masked


def test_policy_detail_and_claims(authed):
    pol = next(p for p in authed.get("/policies").json() if p["category"] == "home")
    detail = authed.get(f"/policies/{pol['id']}").json()
    assert detail["endorsements"][0]["code"] == "HO-WB"
    claims = authed.get("/claims").json()
    denied = next(c for c in claims if c["status"] == "denied")
    assert "denial_analysis" in authed.get(f"/claims/{denied['id']}").json()


def test_search(authed):
    results = authed.get("/search", params={"q": "water damage"}).json()
    assert results and any(r["type"] in ("document", "claim", "policy") for r in results)


def test_document_upload_ingests_and_isolates(authed, client):
    files = {"file": ("renewal-notice.txt", b"RENEWAL NOTICE\nYour new premium is $1,916. Please review by March 3, 2026.", "text/plain")}
    r = authed.post("/documents", files=files)
    assert r.status_code == 202
    doc_id = r.json()["id"]
    doc = authed.get(f"/documents/{doc_id}").json()
    assert doc["status"] == "ready" and doc["doc_type"] == "renewal_notice"
    assert 1916.0 in doc["extracted"]["monetary_amounts"]
    assert authed.get("/documents/not-a-real-id").status_code == 404
    assert authed.post("/documents", files={"file": ("x.exe", b"MZ", "application/octet-stream")}).status_code == 415


def test_chat_streams_events(authed):
    with authed.stream("POST", "/ai/chat", json={"message": "Show my deductibles", "page": {}}) as r:
        assert r.status_code == 200
        events = [json.loads(line[6:]) for line in r.iter_lines() if line.startswith("data: ")]
    types = [e["type"] for e in events]
    assert types[0] == "conversation" and "status" in types and "token" in types and types[-1] == "done"
    done = events[-1]["message"]
    assert done["agent"] == "Policy Intelligence Agent" and done["explain"]["reasoning_summary"]


def test_hitl_approve_flow(authed):
    action = authed.post("/ai/actions/send-draft", json={"to": "adjuster@example.com", "subject": "Docs", "body": "Hi"}).json()
    assert action["status"] == "pending"
    done = authed.post(f"/ai/actions/{action['id']}/approve").json()
    assert done["status"] == "executed" and done["result"]["status"].startswith("delivered")
    assert authed.post(f"/ai/actions/{action['id']}/approve").status_code == 409


def test_explain_this(authed):
    r = authed.post("/ai/explain", json={"kind": "term", "ref": "coinsurance"}).json()
    assert r["simple"] and r["confidence"] == "high"


def test_privacy_center_and_export(authed):
    p = authed.get("/privacy").json()
    assert p["consents"] and p["integrations"]
    assert authed.get("/privacy/export").headers["content-type"].startswith("application/json")


def test_evaluation_permission_and_run(authed):
    run = authed.post("/ai/evaluations/run").json()
    assert run["metrics"]["cases"] >= 6
    assert run["metrics"]["routing_accuracy"] >= 0.75
    assert run["metrics"]["faithfulness"] >= 0.8


def test_validation_errors_are_friendly(authed):
    r = authed.post("/claims/decision", json={"repair_estimate": -5})
    assert r.status_code == 422 and r.json()["errors"]
