"""Document ingestion: extract → OCR → classify → chunk → embed → store → structured extraction."""

import re
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models import Document, DocumentChunk
from app.integrations.ocr import get_ocr_engine
from app.rag.chunking import Page, chunk_pages
from app.rag.embeddings import get_embedder

log = get_logger(__name__)

DOC_TYPE_SIGNALS: dict[str, list[str]] = {
    "policy": ["declarations", "policy period", "insuring agreement", "coverage a", "exclusions", "endorsement"],
    "eob": ["explanation of benefits", "this is not a bill", "allowed amount", "plan paid", "patient responsibility"],
    "medical_bill": ["statement date", "amount due", "patient account", "hospital", "cpt", "charges"],
    "claim_letter": ["claim number", "adjuster", "we have reviewed your claim", "denied", "determination"],
    "renewal_notice": ["renewal", "your new premium", "renews on", "premium change"],
    "repair_estimate": ["estimate", "labor", "parts", "body shop", "repair"],
    "police_report": ["police", "officer", "incident report", "case number"],
    "quote": ["quote", "quoted premium", "valid until"],
    "insurance_card": ["member id", "group number", "rx bin", "id card"],
}

MONEY = re.compile(r"\$\s?([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)")
DATE = re.compile(
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.? \d{1,2}, \d{4}\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b"
)
DEADLINE_HINT = re.compile(r"(?:within|by|no later than|before)\s+([^.\n]{3,60})", re.IGNORECASE)
ACTION_HINT = re.compile(r"(?:please|you must|you need to|required to)\s+([^.\n]{5,120})", re.IGNORECASE)


def classify(text: str) -> tuple[str, str]:
    lower = text.lower()
    scores = {k: sum(1 for s in v if s in lower) for k, v in DOC_TYPE_SIGNALS.items()}
    best = max(scores, key=lambda k: scores[k])
    hits = scores[best]
    if hits == 0:
        return "unknown", "needs_verification"
    confidence = "high" if hits >= 3 else "moderate" if hits == 2 else "needs_verification"
    return best, confidence


def extract_structured(text: str) -> dict:
    amounts = sorted({float(m.replace(",", "")) for m in MONEY.findall(text)}, reverse=True)
    return {
        "monetary_amounts": amounts[:12],
        "dates": list(dict.fromkeys(DATE.findall(text)))[:12],
        "deadlines": [d.strip() for d in DEADLINE_HINT.findall(text)][:6],
        "action_items": [a.strip().rstrip(",;") for a in ACTION_HINT.findall(text)][:6],
        "policy_terms": sorted(
            {t for t in ("deductible", "coinsurance", "copay", "exclusion", "endorsement", "limit", "premium",
                         "prior authorization", "out-of-pocket", "liability", "collision", "comprehensive")
             if t in text.lower()}
        ),
    }


def summarize_extractively(text: str, doc_type: str) -> str:
    lines = [ln.strip() for ln in text.splitlines() if len(ln.strip()) > 40]
    lead = " ".join(lines[:2])[:420]
    label = doc_type.replace("_", " ")
    return f"This looks like a {label}. {lead}" if lead else f"This looks like a {label}."


def read_pages(path: Path, mime_type: str) -> list[Page]:
    if mime_type == "application/pdf" or path.suffix.lower() == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        pages = [Page(i + 1, p.extract_text() or "") for i, p in enumerate(reader.pages)]
        if sum(len(p.text.strip()) for p in pages) < 40:
            ocr = get_ocr_engine()
            return [Page(i + 1, t) for i, t in enumerate(ocr.pdf_to_text(path))]
        return pages
    if mime_type.startswith("image/"):
        return [Page(1, get_ocr_engine().image_to_text(path))]
    return [Page(1, path.read_text(encoding="utf-8", errors="ignore"))]


def index_pages(db: Session, document: Document, pages: list[Page], category: str | None = None) -> int:
    chunks = chunk_pages(pages)
    if not chunks:
        return 0
    vectors = get_embedder().embed([f"{c.section or ''}\n{c.content}" for c in chunks])
    for c, vec in zip(chunks, vectors):
        db.add(
            DocumentChunk(
                document_id=document.id,
                user_id=document.user_id,
                policy_id=document.policy_id,
                claim_id=document.claim_id,
                ordinal=c.ordinal,
                section=c.section,
                page=c.page,
                content=c.content,
                token_count=c.token_count,
                meta={"category": category, "doc_type": document.doc_type},
                embedding=vec,
            )
        )
    document.page_count = max(p.number for p in pages)
    return len(chunks)


def ingest_document(db: Session, document: Document, path: Path, category: str | None = None) -> Document:
    try:
        pages = read_pages(path, document.mime_type)
        full_text = "\n".join(p.text for p in pages)
        doc_type, confidence = classify(full_text)
        if document.doc_type in ("unknown", "", None):
            document.doc_type = doc_type
        document.classification_confidence = confidence
        document.extracted = extract_structured(full_text)
        document.summary = summarize_extractively(full_text, document.doc_type)
        index_pages(db, document, pages, category)
        document.status = "ready" if full_text.strip() else "failed"
    except Exception as exc:  # surface failures to the user rather than crash ingestion
        log.exception("ingestion failed", extra={"fields": {"document_id": document.id}})
        document.status = "failed"
        document.summary = f"We couldn't read this file ({type(exc).__name__})."
    db.commit()
    return document
