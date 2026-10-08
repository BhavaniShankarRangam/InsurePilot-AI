from celery import Celery

from app.core.config import get_settings

settings = get_settings()
celery_app = Celery("insurepilot", broker=settings.celery_broker_url or "memory://", backend=None)
celery_app.conf.update(task_acks_late=True, worker_prefetch_multiplier=1, task_serializer="json", accept_content=["json"])


@celery_app.task(name="insurepilot.ingest_document")
def ingest_document_task(document_id: str, path: str, category: str | None = None) -> None:
    from app.workers.tasks import ingest_document_job

    ingest_document_job(document_id, path, category)
