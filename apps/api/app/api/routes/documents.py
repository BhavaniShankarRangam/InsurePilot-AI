import mimetypes
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.api.deps import DB, CurrentUser, PortfolioDep
from app.core.config import get_settings
from app.db.base import new_id
from app.db.models import Document
from app.services import serializers as ser
from app.services.audit import audit
from app.workers.tasks import enqueue_ingestion

router = APIRouter(prefix="/documents", tags=["documents"])
ALLOWED = {"application/pdf", "image/jpeg", "image/png", "image/webp", "text/plain"}


def _owned(db, user_id: str, doc_id: str) -> Document:
    doc = db.get(Document, doc_id)
    if doc is None or doc.user_id != user_id:  # document-level access control
        raise HTTPException(404, "Document not found")
    return doc


@router.get("")
def list_documents(p: PortfolioDep, doc_type: str | None = None) -> list[dict]:
    return [ser.document_out(d) for d in p.documents if doc_type is None or d.doc_type == doc_type]


@router.post("", status_code=202)
async def upload_document(background: BackgroundTasks, user: CurrentUser, db: DB, p: PortfolioDep,
                          file: UploadFile = File(...), policy_id: str | None = Form(None), claim_id: str | None = Form(None),
                          title: str | None = Form(None)) -> dict:
    ctype = file.content_type or mimetypes.guess_type(file.filename or "")[0] or ""
    if ctype not in ALLOWED:
        raise HTTPException(415, "Upload a PDF, image (JPG/PNG/WEBP) or text file")
    data = await file.read()
    if len(data) > get_settings().max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"Files must be under {get_settings().max_upload_mb} MB")
    if policy_id and p.policy_by_id(policy_id) is None:
        raise HTTPException(400, "Unknown policy")
    if claim_id and p.claim_by_ref(claim_id) is None:
        raise HTTPException(400, "Unknown claim")
    safe_name = Path(file.filename or "upload").name[:180]
    key = f"{user.id}/{uuid4().hex}{Path(safe_name).suffix.lower()[:6]}"
    dest = get_settings().upload_dir / key
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    category = p.policy_by_id(policy_id).category if policy_id else None
    doc = Document(id=new_id(), user_id=user.id, policy_id=policy_id, claim_id=claim_id, title=title or Path(safe_name).stem.replace("-", " ").replace("_", " ").title(),
                   filename=safe_name, mime_type=ctype, size_bytes=len(data), storage_key=key, status="processing")
    db.add(doc)
    audit(db, user.id, "document.uploaded", resource_type="document", resource_id=doc.id, details={"type": ctype})
    db.commit()
    mode = enqueue_ingestion(background, doc.id, str(dest), category)
    return {**ser.document_out(doc), "processing_mode": mode}


@router.get("/{doc_id}")
def get_document(doc_id: str, user: CurrentUser, db: DB) -> dict:
    doc = _owned(db, user.id, doc_id)
    from app.db.models import DocumentChunk

    chunks = db.scalars(select(DocumentChunk).where(DocumentChunk.document_id == doc.id).order_by(DocumentChunk.ordinal)).all()
    return {**ser.document_out(doc), "sections": [{"section": c.section, "page": c.page, "text": c.content} for c in chunks]}


@router.get("/{doc_id}/file")
def download(doc_id: str, user: CurrentUser, db: DB) -> FileResponse:
    doc = _owned(db, user.id, doc_id)
    if not doc.storage_key:
        raise HTTPException(404, "This demo document has no original file")
    path = (get_settings().upload_dir / doc.storage_key).resolve()
    if get_settings().upload_dir.resolve() not in path.parents:
        raise HTTPException(400, "Invalid path")
    audit(db, user.id, "document.downloaded", resource_type="document", resource_id=doc.id)
    db.commit()
    return FileResponse(path, media_type=doc.mime_type, filename=doc.filename)


@router.delete("/{doc_id}", status_code=204)
def delete_document(doc_id: str, user: CurrentUser, db: DB) -> None:
    doc = _owned(db, user.id, doc_id)
    if doc.storage_key:
        (get_settings().upload_dir / doc.storage_key).unlink(missing_ok=True)
    db.delete(doc)
    audit(db, user.id, "document.deleted", resource_type="document", resource_id=doc_id)
    db.commit()
