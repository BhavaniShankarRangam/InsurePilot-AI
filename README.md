# InsurePilot AI

**Insurance, finally understandable.** A personal AI insurance operating system: one assistant that understands
your policies, claims, health benefits and documents, explains them in plain English, watches for problems,
and takes actions only with your approval.

The whole product runs on a realistic **synthetic demo profile** (Alex Morgan: auto, home, health, life, pet,
and travel policies; an open auto claim; a denied water claim; a medical bill with a possible discrepancy; a
pending MRI authorization). It needs no carrier integrations or API keys.

---

## Quick start (local, no Docker)

Requirements: Python 3.12+, Node 20.9+ (24 recommended).

```bash
# 1. API (FastAPI) — SQLite + local embeddings by default, demo data seeded on startup
cd apps/api
python -m venv .venv
.venv/Scripts/pip install -r requirements-dev.txt      # macOS/Linux: .venv/bin/pip
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000

# 2. Web (Next.js) — in a second terminal
cd apps/web
npm install
API_URL=http://127.0.0.1:8000 npm run dev               # PowerShell: $env:API_URL="http://127.0.0.1:8000"; npm run dev
```

Open http://localhost:3000 → **Try InsurePilot** → **Explore the live demo**.

Or run both with one command: `./scripts/dev.ps1` (Windows) or `./scripts/dev.sh` (macOS/Linux/Git Bash).
If port 8000 is taken, pass another port (`-ApiPort 8010` / `API_PORT=8010`).

Demo credentials (for the password login): `demo@insurepilot.ai` / `DemoPilot!2026`.
API docs: http://localhost:8000/docs

## Quick start (Docker: Postgres + pgvector, Redis, Celery)

```bash
cp apps/api/.env.example .env      # optional: add LLM keys
docker compose up --build
```

Services: `web` :3000 · `api` :8000 · `worker` (Celery document ingestion) · `db` (Postgres 17 + pgvector) · `redis`.

## Turning on a real LLM

The app works fully in **demo mode** (`LLM_PROVIDER=mock`). Agents build grounded answers from structured
data, tool results and retrieved passages, and the mock provider streams those answers unchanged. Live
models only rephrase that evidence; they're instructed never to add facts.

| Variable | Values |
|---|---|
| `LLM_PROVIDER` | `mock` (default), `anthropic`, `openai`, `gemini` |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY` | provider key |
| `LLM_MODEL_LARGE` / `LLM_MODEL_SMALL` | override routing (defaults: `claude-opus-5-5` / `claude-haiku-4-5` on Anthropic) |
| `EMBEDDING_PROVIDER` | `local` (hashing, offline) or `openai` |
| `LANGSMITH_API_KEY` | enables LangGraph tracing |

Cost routing: small models handle intent, extraction, classification and summaries. Large models handle
coverage reasoning, claims, comparisons, cross-document analysis and drafting (`app/ai/llm/router.py`).
Token usage, latency, errors and cost are recorded per call and shown on **AI Evaluations**.

## Architecture

```
Browser ──► Next.js 16 (App Router, React 19)  ── /api/* rewrite (same-origin, httpOnly cookie) ──►  FastAPI
            Tailwind v4 · shadcn-style UI · Framer Motion                                         │
            React Three Fiber (Insurance Universe, hero) · Zustand · TanStack Query               │
                                                                                                   ▼
                     ┌──────────────── LangGraph Supervisor ────────────────┐
  SSE stream ◄────── │ understand → route → specialist agent → guardrails   │ ──► composer (LLM router)
  (user-safe         └───────────────────────┬──────────────────────────────┘
   progress only)                            │ tool calls (permission-tiered)
                                             ▼
                     MCP tool registry (read / draft / external→approval)
                        │            │                 │                     │
                Digital Twin     Hybrid RAG       Adapters (mock today)   Human-in-the-loop
                (Postgres +      BM25 + vector     carrier REST · FHIR      AIAction approvals
                 graph edges)    + RRF + rerank     payer · providers ·      + audit log
                                 + citations        quotes · email · OCR
```

**Agents** (`apps/api/app/ai/agents/`): Policy Intelligence, Claims, Coverage, Billing, Renewal, Insurance
Shopping, Risk, Document Intelligence, Medical Insurance, Provider Network, Communication, Fraud Signal and
Human Escalation. Each declares its tools, permissions and escalation rules. Each returns a structured
`AgentOutput` with a confidence level (`high` / `moderate` / `needs_verification` / `human_review`), a
reasoning summary, citations, cards and proposed actions. The supervisor's guardrail node blocks any
policy-specific answer that has no supporting data or citation.

**RAG** (`apps/api/app/rag/`): ingest → OCR → classify → section-aware chunking (page numbers kept) → embed →
pgvector (JSON on SQLite) + BM25 → reciprocal-rank fusion → rerank → context compression → cited answers
(e.g. *Auto Policy · Section 4 — Collision Coverage · Page 18*). Evaluation runs a golden set and measures
faithfulness, answer relevance, context precision, recall and relevance, citation accuracy, hallucination
risk, routing accuracy, latency and cost.

## Project structure

```
apps/
  api/                    FastAPI service
    app/core/             config, JWT/RBAC, field encryption, PII masking, rate limiting, JSON logging
    app/db/models/        35 tables: identity, assets, policies, claims, documents, health, AI, graph
    app/rag/              chunking, embeddings, hybrid retriever, ingestion, evaluation
    app/ai/               LLM providers + router, agents, LangGraph supervisor, streaming orchestrator
    app/mcp/              tool registry (HITL tiers), tool catalog, MCP server
    app/integrations/     carrier / FHIR / provider / quotes / email / OCR adapters (+ mocks)
    app/services/         health score & risk engine, claims, health benefits, policy intel, search…
    app/api/routes/       auth, portfolio, claims, documents, health, ai, account/privacy
    app/demo/             synthetic policies + seed
    tests/                pytest: security, RAG, services, agents, API, evaluation
  web/                    Next.js app
    src/app/              landing, auth, onboarding, (platform)/… pages
    src/components/ai/    orb, command center, chat, cards, approval, explain-this, voice
    src/components/three/ 3D models, Insurance Universe, hero scene
    tests/                Vitest unit tests + Playwright e2e
docs/                     MCP setup
scripts/                  dev launchers
docker-compose.yml        full stack
.github/workflows/ci.yml  tests, lint, build, e2e, docker build
```

## Testing

```bash
cd apps/api && .venv/Scripts/python -m pytest -q        # 59 tests
cd apps/web && npm run typecheck && npm run lint && npm test   # 13 unit tests
cd apps/web && npx playwright install chromium && npm run test:e2e   # needs both servers running
```

## Security & privacy

- **Sessions:** JWT in an httpOnly, SameSite=Lax cookie, behind a same-origin proxy. Bearer tokens and the OAuth2 password grant are available for API clients.
- **CSRF:** cookie-authenticated mutations must send a custom client header.
- **Access control:** RBAC (customer / agent / analyst / admin). Every document, claim and action is scoped to its owner.
- **Encryption:** Fernet field encryption at rest for policy numbers, member IDs, VINs, addresses, beneficiaries, DOB and phone. Set `FIELD_ENCRYPTION_KEY` in production.
- **Logging:** PII masking in logs and audit records. Request logs record paths only, never bodies or query strings.
- **Rate limiting:** Redis when available, otherwise in-memory.
- **Headers & uploads:** security headers on every response; upload type and size validation; path-traversal checks.
- **Privacy Center:** data inventory, consent toggles, integration revocation, JSON export and account deletion.

High-impact actions (submit claim, send email, share medical data, escalate) always create a pending approval
showing **what** the AI will do, **why**, and **what will be shared**. Nothing executes until you approve.

## What's real vs. mocked

| Area | Status |
|---|---|
| UI, agents, supervisor, RAG, evaluation, HITL, auth, privacy | Implemented and tested |
| LLM providers | Anthropic (official SDK), OpenAI, Gemini adapters; mock provider by default |
| Carrier APIs, FHIR payer, provider directory, quote marketplace, email | Production-shaped adapter interfaces with **mock implementations** |
| OCR | Tesseract when installed (included in the API Docker image); otherwise text/PDF-text only |
| Claim Photo AI | Rule-based observations from filename, description and metadata, clearly labeled; plug a vision model into `services/claims.py` |
| Voice | Browser Web Speech API (Chrome/Edge); spoken replies via speechSynthesis |
| RAGAS | Hook in `rag/evaluation.py`; custom offline metrics run today |
| Postgres + pgvector path | SQL validated against the Postgres dialect; exercised via Docker Compose (not run in this dev environment) |

## Disclaimer

InsurePilot explains coverage; insurers make coverage decisions. The Insurance Health Score, simulations and
savings are guidance, not financial, legal or medical advice.
