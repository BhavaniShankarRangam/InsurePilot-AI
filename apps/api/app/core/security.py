"""Password hashing, JWT sessions, field-level encryption and role permissions."""

import base64
import hashlib
from datetime import UTC, datetime, timedelta
from enum import StrEnum

import bcrypt
import jwt
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings

JWT_ALGORITHM = "HS256"


class Role(StrEnum):
    CUSTOMER = "customer"
    AGENT = "agent"
    ANALYST = "analyst"
    ADMIN = "admin"


class Permission(StrEnum):
    READ_OWN = "data:read_own"
    WRITE_OWN = "data:write_own"
    AI_CHAT = "ai:chat"
    AI_APPROVE = "ai:approve_actions"
    EVAL_READ = "eval:read"
    AUDIT_READ = "audit:read"
    ADMIN = "admin:all"


ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.CUSTOMER: {Permission.READ_OWN, Permission.WRITE_OWN, Permission.AI_CHAT, Permission.AI_APPROVE},
    Role.AGENT: {Permission.READ_OWN, Permission.AI_CHAT, Permission.AUDIT_READ},
    Role.ANALYST: {Permission.EVAL_READ, Permission.AUDIT_READ},
    Role.ADMIN: set(Permission),
}


def permissions_for(roles: list[str]) -> set[Permission]:
    granted: set[Permission] = set()
    for r in roles:
        try:
            granted |= ROLE_PERMISSIONS[Role(r)]
        except ValueError:
            continue
    return granted


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def create_access_token(subject: str, roles: list[str], minutes: int | None = None) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "roles": roles,
        "iat": now,
        "exp": now + timedelta(minutes=minutes or settings.access_token_minutes),
        "iss": "insurepilot",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(
            token, get_settings().secret_key, algorithms=[JWT_ALGORITHM], issuer="insurepilot"
        )
    except jwt.PyJWTError:
        return None


def _fernet() -> Fernet:
    settings = get_settings()
    key = settings.field_encryption_key
    if not key:
        # Derive a stable dev key from SECRET_KEY so local data stays readable across restarts.
        key = base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode()).digest()).decode()
    return Fernet(key.encode())


def encrypt_value(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_value(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        return "[unreadable]"
