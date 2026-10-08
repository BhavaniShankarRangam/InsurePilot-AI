from app.services.claims import claim_decision, denial_analysis
from app.services.health_benefits import procedure_check, reconcile
from app.services.health_score import detect_risks, expected_coinsurance, health_score, home_layout
from app.services.policy_intel import compare, premium_change, simulate


def test_health_score_explains_itself(portfolio):
    hs = health_score(portfolio)
    assert 0 <= hs["score"] <= 100
    assert hs["factors"] and hs["positives"]
    assert "not financial" in hs["disclaimer"]


def test_risks_mark_uncertainty(portfolio):
    risks = {r.kind: r for r in detect_risks(portfolio)}
    assert risks["underinsurance"].certainty == "possible"
    assert risks["missing_claim_document"].certainty == "confirmed"
    assert risks["billing_discrepancy"].certainty == "possible"
    assert "missing_beneficiary" in risks


def test_layout_prioritizes_recent_claim(portfolio):
    assert home_layout(portfolio)[0] == "claims"


def test_claim_decision_math_never_decides(portfolio):
    d = claim_decision(portfolio, "auto", 1200)
    assert d["deductible"] == 1000
    assert d["estimated_insurer_payment"] == 200
    assert "not a recommendation" in d["note"]
    assert len(d["options"]) == 2


def test_denial_analysis_finds_endorsement(portfolio):
    claim = next(c for c in portfolio.claims if c.status == "denied")
    a = denial_analysis(portfolio, claim)
    kinds = {f["kind"] for f in a["findings"]}
    assert {"exclusion", "endorsement"} <= kinds
    assert "depends on the actual cause of loss" in a["explanation"]


def test_reconciliation_flags_coinsurance(portfolio):
    r = reconcile(portfolio, portfolio.bills[0], portfolio.eobs[0])
    titles = [i["title"] for i in r["issues"]]
    assert "Coinsurance higher than expected" in titles
    assert expected_coinsurance(4300, 2000, 0, 20) == 460


def test_procedure_check_in_network(portfolio):
    r = procedure_check(portfolio, "MRI lumbar spine", "Lakeside Imaging")
    assert r["in_network"] is True and r["cpt"] == "72148"
    assert r["estimate"]["you_pay"] > 0
    assert any(s["step"] == "Check authorization" and s["status"] == "warning" for s in r["steps"])


def test_premium_change_separates_confirmed_and_possible(portfolio):
    pc = premium_change(portfolio.policy("auto"))
    assert pc["change_percent"] == 19
    assert pc["confirmed"] and pc["possible"]


def test_comparison_does_not_rank(portfolio):
    c = compare(portfolio, "auto")
    assert c["columns"][0]["current"] is True
    assert "best" not in str(c["tradeoffs"]).lower()


def test_simulation_is_labeled(portfolio):
    s = simulate(portfolio, "deductible", {"category": "auto", "from": 1000, "to": 2000})
    assert s["label"] == "Simulated outcome" and "not a quote" in s["disclaimer"]
