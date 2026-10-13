from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.api.deps import DB, CurrentUser, clear_session_cookie, client_ip, cookie_kwargs
from app.core.config import get_settings
from app.core.rate_limit import rate_limit
from app.core.security import create_access_token, hash_password, permissions_for, verify_password
from app.db.models import Consent, User
from app.demo.seed import seed_demo
from app.schemas.api import AuthOut, LoginIn, RegisterIn, UserOut
from app.services.audit import audit

router = APIRouter(prefix="/auth", tags=["auth"])
auth_limit = Depends(rate_limit("auth", 10))


def user_out(u: User) -> UserOut:
    return UserOut(id=u.id, email=u.email, full_name=u.full_name, preferred_name=u.preferred_name, roles=u.roles,
                   is_demo=u.is_demo, onboarding_complete=u.onboarding_complete, preferences=u.preferences or {},
                   permissions=sorted(p.value for p in permissions_for(u.roles)))


def _session(response: Response, db, user: User, request: Request, action: str) -> AuthOut:
    token = create_access_token(user.id, user.roles)
    response.set_cookie(get_settings().session_cookie_name, token, **cookie_kwargs())
    user.last_login_at = datetime.now(UTC)
    audit(db, user.id, action, ip=client_ip(request))
    db.commit()
    return AuthOut(user=user_out(user), access_token=token)


@router.post("/register", response_model=AuthOut, status_code=201, dependencies=[auth_limit])
def register(body: RegisterIn, request: Request, response: Response, db: DB) -> AuthOut:
    if db.scalar(select(User).where(User.email == body.email.lower())):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")
    user = User(email=body.email.lower(), password_hash=hash_password(body.password), full_name=body.full_name,
                preferred_name=body.full_name.split()[0], roles=["customer"], preferences={"theme": "system"})
    db.add(user)
    db.flush()
    db.add(Consent(user_id=user.id, scope="documents.ai_processing",
                   purpose="Let AI read your uploaded documents to explain and organize them."))
    return _session(response, db, user, request, "auth.register")


@router.post("/login", response_model=AuthOut, dependencies=[auth_limit])
def login(body: LoginIn, request: Request, response: Response, db: DB) -> AuthOut:
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user is None or not verify_password(body.password, user.password_hash):
        audit(db, None, "auth.login_failed", ip=client_ip(request), details={"email_domain": body.email.split("@")[-1]})
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email or password is incorrect")
    return _session(response, db, user, request, "auth.login")


@router.post("/token", dependencies=[auth_limit])
def oauth2_token(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DB) -> dict:
    """OAuth2 password grant for API clients (Swagger 'Authorize', integrations)."""
    user = db.scalar(select(User).where(User.email == form.username.lower()))
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    return {"access_token": create_access_token(user.id, user.roles), "token_type": "bearer"}


@router.post("/demo", response_model=AuthOut, dependencies=[auth_limit])
def demo_login(request: Request, response: Response, db: DB) -> AuthOut:
    """Signs into the synthetic demo profile (Alex Morgan). Creates it on first use."""
    user = seed_demo(db)
    return _session(response, db, user, request, "auth.demo_login")


@router.post("/logout", status_code=204)
def logout(response: Response) -> Response:
    clear_session_cookie(response)
    response.status_code = 204
    return response


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    return user_out(user)
