import os
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import app.mcp.tools  # noqa: F401  (registers the tool catalog)
from app.api.routes import account, ai, auth, claims, documents, health, portfolio
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.session import SessionLocal, init_db

settings = get_settings()
configure_logging(settings.log_level)
log = get_logger("insurepilot")

if settings.langsmith_api_key:  # LangGraph/LangChain pick these up for tracing
    os.environ.setdefault("LANGSMITH_TRACING", "true")
    os.environ.setdefault("LANGSMITH_API_KEY", settings.langsmith_api_key)
    os.environ.setdefault("LANGSMITH_PROJECT", settings.langsmith_project)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    if os.getenv("SEED_DEMO", "true").lower() == "true":
        from app.demo.seed import seed_demo

        with SessionLocal() as db:
            seed_demo(db)
    log.info("InsurePilot API ready", extra={"fields": {"llm_provider": settings.llm_provider, "db": settings.database_url.split(":")[0]}})
    yield


app = FastAPI(
    title="InsurePilot AI API",
    version="1.0.0",
    description="Personal AI Insurance Operating System — policies, claims, health benefits, agents and RAG.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-InsurePilot-Client"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = int((time.perf_counter() - start) * 1000)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Cache-Control"] = response.headers.get("Cache-Control", "no-store")
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    # Paths only — never log bodies, query strings or headers (they may contain PII or tokens).
    log.info("request", extra={"fields": {"id": request_id, "method": request.method, "path": request.url.path,
                                          "status": response.status_code, "ms": elapsed}})
    return response


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [{"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": "Please check the highlighted fields.", "errors": errors})


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled error")
    return JSONResponse(status_code=500, content={"detail": "Something went wrong on our side. Please try again."})


for r in (auth.router, portfolio.router, claims.router, documents.router, health.router, ai.router, account.router):
    app.include_router(r)


@app.get("/healthz", tags=["system"])
def healthz() -> dict:
    return {"status": "ok", "service": "insurepilot-api"}
