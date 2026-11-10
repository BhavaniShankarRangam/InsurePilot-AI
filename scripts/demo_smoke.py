"""End-to-end smoke test against a running InsurePilot URL (local or the live demo Space).

    python scripts/demo_smoke.py https://<user>-<space>.hf.space

Walks the recruiter flow through the public web entry point (Next.js → /api proxy):
landing page → one-click demo login → sample triage queue (5 claims, every route) → run a triage →
claims list. With --check-limits it also confirms the demo guardrails: an oversized upload is rejected and the
hourly claim cap returns 429 (this uses up the caller's hourly quota, so it runs last).
Standard library only, so it runs anywhere Python does.
"""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import date, timedelta

EXPECTED = {"TRI-1001": "auto_approve", "TRI-1002": "auto_approve", "TRI-1003": "fraud_review",
            "TRI-1004": "not_covered", "TRI-1005": "low_confidence"}


class Client:
    def __init__(self, base: str) -> None:
        self.base = base.rstrip("/")
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def call(self, method: str, path: str, body: dict | None = None, raw: bytes | None = None,
             ctype: str | None = None, timeout: int = 60) -> tuple[int, object]:
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request(self.base + path, data=data, method=method)
        req.add_header("X-InsurePilot-Client", "web")
        if ctype or body is not None:
            req.add_header("Content-Type", ctype or "application/json")
        try:
            with self.opener.open(req, timeout=timeout) as r:
                text = r.read().decode(errors="replace")
                code = r.status
        except urllib.error.HTTPError as e:
            text, code = e.read().decode(errors="replace"), e.code
        try:
            return code, json.loads(text)
        except json.JSONDecodeError:
            return code, text


def triage_body(**over) -> dict:
    t = date.today()
    b = {"incident_type": "glass", "vehicle_use": "commute",
         "description": "Rock from a gravel truck chipped the windshield and it cracked across the driver's side.",
         "incident_date": str(t - timedelta(days=1)), "reported_date": str(t),
         "policy_start_date": str(t - timedelta(days=120)), "policy_end_date": str(t + timedelta(days=245)),
         "amount_claimed": 900, "vehicle_value": 24000, "photos": 2}
    b.update(over)
    return b


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--wait", type=int, default=0, help="seconds to wait for the app to come up (Spaces cold-start)")
    ap.add_argument("--check-limits", action="store_true")
    args = ap.parse_args()
    c = Client(args.url)
    failures: list[str] = []

    def check(name: str, ok: bool, detail: object = "") -> None:
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  → {str(detail)[:300]}"))
        if not ok:
            failures.append(name)

    deadline = time.time() + args.wait
    while True:
        code, body = c.call("GET", "/", timeout=30)
        if code == 200 or time.time() > deadline:
            break
        time.sleep(10)
    check("landing page loads", code == 200 and "InsurePilot" in str(body), code)

    code, body = c.call("POST", "/api/auth/demo", {})
    check("one-click demo login", code == 200 and isinstance(body, dict) and body.get("user", {}).get("is_demo"), body)

    code, q = c.call("GET", "/api/claims/triage/queue")
    items = q.get("items", []) if isinstance(q, dict) else []
    got = {i["claim_number"]: i["result"]["path"] for i in items}
    check("5 sample claims loaded", len(items) == 5, q)
    for num, path in EXPECTED.items():
        check(f"{num} routes to {path}", got.get(num) == path, got.get(num))
    limits = q.get("limits", {}) if isinstance(q, dict) else {}
    print(f"     limits reported by server: {limits}")

    code, r = c.call("POST", "/api/claims/triage", triage_body())
    check("visitor triage run (auto-approve)", code == 200 and r.get("path") == "auto_approve", r)
    code, r = c.call("POST", "/api/claims/triage", triage_body(vehicle_use="rideshare"))
    check("visitor triage run (rideshare → not covered)", code == 200 and r.get("path") == "not_covered", r)

    code, claims = c.call("GET", "/api/claims")
    check("claims page data", code == 200 and isinstance(claims, list) and len(claims) >= 1, claims)

    code, page = c.call("GET", "/triage")
    check("triage page renders", code == 200 and "<html" in str(page).lower(), code)

    if args.check_limits:
        if not limits.get("demo_mode"):
            check("server is in demo mode", False, limits)
        else:
            mb = int(limits.get("max_upload_mb") or 2)
            boundary = uuid.uuid4().hex
            payload = b"%PDF-1.4\n" + b"0" * (mb * 1024 * 1024 + 1024)
            raw = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"big.pdf\"\r\n"
                   f"Content-Type: application/pdf\r\n\r\n").encode() + payload + f"\r\n--{boundary}--\r\n".encode()
            code, r = c.call("POST", "/api/documents", raw=raw, ctype=f"multipart/form-data; boundary={boundary}", timeout=120)
            check(f"upload over {mb} MB rejected (413)", code == 413, (code, r))

            cap = int(limits.get("claims_per_hour") or 10)
            codes = [c.call("POST", "/api/claims/triage", triage_body())[0] for _ in range(cap + 1)]
            check(f"hourly claim cap enforced (429 by run {cap + 1})", 429 in codes, codes)

    print(f"\n{'ALL PASSED' if not failures else f'{len(failures)} FAILED'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
