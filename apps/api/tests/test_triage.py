from datetime import date, timedelta

import pytest

from app.core.config import get_settings
from app.core.rate_limit import get_limiter
from app.demo.triage_samples import _samples
from app.services.triage import intake_from_dict, triage


@pytest.mark.parametrize("sample", _samples(date.today()), ids=lambda s: s["claim_number"])
def test_each_sample_lands_on_its_path(sample):
    assert triage(intake_from_dict(sample["intake"]))["path"] == sample["expected_path"]


def test_samples_cover_every_requested_path():
    paths = {s["expected_path"] for s in _samples(date.today())}
    assert {"auto_approve", "fraud_review", "not_covered", "low_confidence"} <= paths
    assert len(_samples(date.today())) == 5


def _base(**over):
    t = date.today()
    d = {"incident_type": "collision", "vehicle_use": "personal", "photos": 3, "vehicle_value": 25000,
         "description": "Rear-ended at a stop light, bumper and trunk lid dented, no injuries reported.",
         "incident_date": t - timedelta(days=2), "reported_date": t - timedelta(days=1),
         "policy_start_date": t - timedelta(days=300), "policy_end_date": t + timedelta(days=60), "amount_claimed": 2000}
    d.update(over)
    return intake_from_dict(d)


def test_auto_approve_pays_amount_minus_deductible():
    r = triage(_base())
    assert r["path"] == "auto_approve" and r["estimated_payout"] == 1000


def test_over_limit_goes_to_adjuster():
    assert triage(_base(amount_claimed=9000))["path"] == "adjuster_review"


def test_incident_outside_policy_period_not_covered():
    t = date.today()
    assert triage(_base(policy_start_date=t - timedelta(days=1)))["path"] == "not_covered"


def test_single_fraud_signal_is_noted_not_flagged():
    r = triage(_base(prior_claims_12mo=3))
    assert r["path"] == "auto_approve"
    assert any(x["rule"] == "Signal noted" for x in r["reasons"])


def test_wear_and_tear_not_covered():
    assert triage(_base(description="Engine failure on the highway after years of wear and tear, car towed home."))["path"] == "not_covered"


# ---- API ----------------------------------------------------------------------
def test_queue_endpoint_returns_five_samples(authed):
    r = authed.get("/claims/triage/queue")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 5
    assert all(i["result"]["path"] == i["expected_path"] for i in items)


def test_triage_endpoint_is_stateless(authed):
    body = {"incident_type": "glass", "description": "Rock chip turned into a long crack across the windshield on I-35.",
            "incident_date": str(date.today()), "reported_date": str(date.today()),
            "policy_start_date": str(date.today() - timedelta(days=100)),
            "policy_end_date": str(date.today() + timedelta(days=100)), "amount_claimed": 800, "vehicle_value": 20000,
            "photos": 1}
    before = len(authed.get("/claims").json())
    r = authed.post("/claims/triage", json=body)
    assert r.status_code == 200 and r.json()["path"] == "auto_approve"
    assert len(authed.get("/claims").json()) == before


def test_triage_rejects_bad_dates(authed):
    body = {"incident_type": "glass", "description": "x", "incident_date": str(date.today()),
            "reported_date": str(date.today() - timedelta(days=3)), "policy_start_date": "2026-01-01",
            "policy_end_date": "2027-01-01", "vehicle_value": 20000}
    assert authed.post("/claims/triage", json=body).status_code == 422


# ---- Demo guardrails ------------------------------------------------------------
@pytest.fixture()
def demo_mode(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "demo_mode", True)
    monkeypatch.setattr(s, "demo_claims_per_hour", 2)
    monkeypatch.setattr(s, "demo_max_upload_mb", 1)
    get_limiter().reset()
    yield s
    get_limiter().reset()


def test_demo_caps_triage_runs_per_hour(authed, demo_mode):
    body = {"incident_type": "other", "description": "Something happened to the car.", "incident_date": str(date.today()),
            "reported_date": str(date.today()), "policy_start_date": "2026-01-01", "policy_end_date": "2027-12-31",
            "vehicle_value": 20000}
    codes = [authed.post("/claims/triage", json=body).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_demo_global_cap(authed, demo_mode, monkeypatch):
    monkeypatch.setattr(demo_mode, "demo_claims_per_hour", 100)
    monkeypatch.setattr(demo_mode, "demo_claims_per_hour_global", 1)
    body = {"incident_type": "other", "description": "Something happened to the car.", "incident_date": str(date.today()),
            "reported_date": str(date.today()), "policy_start_date": "2026-01-01", "policy_end_date": "2027-12-31",
            "vehicle_value": 20000}
    assert authed.post("/claims/triage", json=body).status_code == 200
    r = authed.post("/claims/triage", json=body)
    assert r.status_code == 429 and "busy" in r.json()["detail"]


def test_demo_rejects_oversized_upload(authed, demo_mode):
    big = b"%PDF-1.4\n" + b"0" * (1024 * 1024 + 10)
    r = authed.post("/documents", files={"file": ("big.pdf", big, "application/pdf")})
    assert r.status_code == 413 and "1 MB" in r.json()["detail"]


def test_demo_forces_mock_llm(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    get_settings.cache_clear()
    try:
        assert get_settings().llm_provider == "mock"
    finally:
        monkeypatch.delenv("DEMO_MODE")
        monkeypatch.delenv("LLM_PROVIDER")
        get_settings.cache_clear()
