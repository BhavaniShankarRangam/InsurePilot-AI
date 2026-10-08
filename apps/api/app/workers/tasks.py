"""Background jobs. Runs on Celery when CELERY_BROKER_URL is set, otherwise in-process."""

from pathlib import Path

from fastapi import BackgroundTasks

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)


def ingest_document_job(document_id: str, path: str, category: str | None = None) -> None:
    from app.db.models import Document, Notification
    from app.db.session import SessionLocal
    from app.rag.ingest import ingest_document
    from app.services.digital_twin import rebuild_graph

    db = SessionLocal()
    try:
        doc = db.get(Document, document_id)
        if doc is None:
            return
        ingest_document(db, doc, Path(path), category)
        db.add(Notification(
            user_id=doc.user_id, category="documents", priority=3, link=f"/documents?doc={doc.id}",
            title=f"{doc.title} is ready" if doc.status == "ready" else f"We couldn't read {doc.title}",
            body=doc.summary or "",
        ))
        rebuild_graph(db, doc.user_id)
        db.commit()
    finally:
        db.close()


def enqueue_ingestion(background: BackgroundTasks, document_id: str, path: str, category: str | None = None) -> str:
    if get_settings().celery_broker_url:
        from app.workers.celery_app import celery_app

        celery_app.send_task("insurepilot.ingest_document", args=[document_id, path, category])
        return "celery"
    background.add_task(ingest_document_job, document_id, path, category)
    return "inline"
