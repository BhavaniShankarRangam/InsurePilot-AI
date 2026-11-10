from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select

from app.api.deps import DB, CurrentUser, PortfolioDep
from app.core.config import get_settings
from app.core.rate_limit import demo_quota, read_upload_capped
from app.db.models import ClaimPhoto, TriageClaim
from app.demo.triage_samples import seed_triage_samples
from app.schemas.api import ClaimDraftIn, DecisionIn, TriageIn
from app.services import claims as svc
from app.services import serializers as ser
from app.services import triage as triage_svc
from app.services.audit import audit

router = APIRouter(prefix="/claims", tags=["claims"])
IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic"}
claims_quota = Depends(demo_quota("claims", "demo_claims_per_hour", "demo_claims_per_hour_global"))


@router.get("")
def list_claims(p: PortfolioDep, status: str | None = None, category: str | None = None) -> list[dict]:
    return [ser.claim_card(c) for c in p.claims
            if (status is None or c.status == status) and (category is None or c.category == category)]


@router.post("", status_code=201, dependencies=[claims_quota])
def create_claim(body: ClaimDraftIn, user: CurrentUser, db: DB, p: PortfolioDep) -> dict:
    pol = p.policy(body.category)
    if pol is None:
        raise HTTPException(400, f"No active {body.category} policy")
    claim = svc.create_claim_draft(db, user.id, pol, body.title, body.description, body.incident_date, body.amount)
    audit(db, user.id, "claim.draft_created", resource_type="claim", resource_id=claim.id)
    db.commit()
    db.refresh(claim)
    return ser.claim_detail(claim, [])


@router.post("/decision")
def decision(body: DecisionIn, p: PortfolioDep) -> dict:
    return svc.claim_decision(p, body.category, body.repair_estimate)


# ---- Triage (carrier view, synthetic queue) -----------------------------------
# Declared before /{claim_id} so "triage" isn't read as a claim id.
@router.get("/triage/queue")
def triage_queue(_: CurrentUser, db: DB) -> dict:
    rows = list(db.scalars(select(TriageClaim).order_by(TriageClaim.sort_order)))
    if not rows:
        seed_triage_samples(db)
        rows = list(db.scalars(select(TriageClaim).order_by(TriageClaim.sort_order)))
    items = [{"id": r.id, "claim_number": r.claim_number, "claimant": r.claimant, "title": r.title,
              "expected_path": r.expected_path, "intake": r.intake,
              "result": triage_svc.triage(triage_svc.intake_from_dict(r.intake))} for r in rows]
    s = get_settings()
    return {"items": items, "limits": {"demo_mode": s.demo_mode, "max_upload_mb": s.upload_limit_mb,
                                       "claims_per_hour": s.demo_claims_per_hour if s.demo_mode else None,
                                       "auto_approve_limit": triage_svc.AUTO_APPROVE_LIMIT}}


@router.post("/triage", dependencies=[claims_quota])
def triage_run(body: TriageIn, user: CurrentUser, db: DB) -> dict:
    """Triage a claim typed in by the visitor. Stateless: nothing is stored, so the shared demo stays clean."""
    result = triage_svc.triage(triage_svc.intake_from_dict(body.model_dump()))
    audit(db, user.id, "claim.triage_run", resource_type="triage", details={"path": result["path"]})
    db.commit()
    return result


@router.get("/{claim_id}")
def get_claim(claim_id: str, p: PortfolioDep) -> dict:
    c = p.claim_by_ref(claim_id)
    if c is None:
        raise HTTPException(404, "Claim not found")
    out = ser.claim_detail(c, [d for d in p.documents if d.claim_id == c.id])
    if c.status == "denied":
        out["denial_analysis"] = svc.denial_analysis(p, c)
    out["packet"] = svc.claim_packet(p, c)
    return out


@router.post("/{claim_id}/photos", status_code=201, dependencies=[claims_quota])
async def upload_photo(claim_id: str, user: CurrentUser, db: DB, p: PortfolioDep, file: UploadFile = File(...),
                       description: str = Form("")) -> dict:
    claim = p.claim_by_ref(claim_id)
    if claim is None:
        raise HTTPException(404, "Claim not found")
    if file.content_type not in IMAGE_TYPES:
        raise HTTPException(415, "Please upload a JPEG, PNG, WEBP or HEIC photo")
    data = await read_upload_capped(file)
    key = f"{user.id}/{uuid4().hex}{Path(file.filename or 'photo.jpg').suffix.lower()[:6]}"
    dest = get_settings().upload_dir / key
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    obs = svc.photo_observations(file.filename or "photo", description, len(data), file.content_type or "")
    photo = ClaimPhoto(claim_id=claim.id, user_id=user.id, filename=file.filename or "photo", storage_key=key, observations=obs)
    db.add(photo)
    if "Photos of damage" in claim.missing_documents:
        claim.missing_documents = [d for d in claim.missing_documents if d != "Photos of damage"]
    audit(db, user.id, "claim.photo_uploaded", resource_type="claim", resource_id=claim.id)
    db.commit()
    return {"id": photo.id, "observations": obs}
