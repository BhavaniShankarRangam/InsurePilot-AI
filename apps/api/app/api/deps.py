from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import Permission, decode_access_token, permissions_for
from app.db.models import User
from app.db.session import get_db
from app.services.portfolio import Portfolio, load_portfolio

DB = Annotated[Session, Depends(get_db)]
UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}


def get_current_user(
    request: Request,
    db: DB,
    authorization: Annotated[str | None, Header()] = None,
    ip_session: Annotated[str | None, Cookie()] = None,
    x_insurepilot_client: Annotated[str | None, Header()] = None,
) -> User:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:]
    elif ip_session:
        token = ip_session
        # CSRF defence for cookie sessions: unsafe methods must carry the custom client header,
        # which cross-site forms cannot set.
        if request.method in UNSAFE and x_insurepilot_client != "web":
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Missing client header")
    payload = decode_access_token(token) if token else None
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    user = db.get(User, payload["sub"])
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session no longer valid")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require(permission: Permission):
    def checker(user: CurrentUser) -> User:
        if permission not in permissions_for(user.roles):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You don't have access to this resource")
        return user

    return checker


def get_portfolio(user: CurrentUser, db: DB) -> Portfolio:
    return load_portfolio(db, user.id)


PortfolioDep = Annotated[Portfolio, Depends(get_portfolio)]


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def cookie_kwargs() -> dict:
    s = get_settings()
    return {"httponly": True, "secure": s.is_production, "samesite": "lax", "path": "/",
            "max_age": s.access_token_minutes * 60}
