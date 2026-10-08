from sqlalchemy.orm import Session

from app.core.masking import mask_dict
from app.db.models import AuditLog


def audit(db: Session, user_id: str | None, action: str, *, actor: str = "user", resource_type: str | None = None,
          resource_id: str | None = None, details: dict | None = None, ip: str | None = None) -> None:
    db.add(AuditLog(user_id=user_id, actor=actor, action=action, resource_type=resource_type, resource_id=resource_id,
                    details=mask_dict(details or {}), ip=ip))
