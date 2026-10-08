from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.exceptions import TooManyRequestsException, UnauthorizedException
from app.core.rate_limit import login_rate_limiter
from app.database.session import get_db
from app.dependencies.auth import get_current_active_user
from app.repositories.user_repo import UserRepository
from app.schemas.user import (
    AuthResponse,
    ChangePasswordRequest,
    Token,
    UserCreate,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

# Brute-force protection: failed logins per (client IP + email).
LOGIN_MAX_FAILURES = 5
LOGIN_WINDOW_SECONDS = 60


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(UserRepository(db))

@router.post("/register", response_model=AuthResponse)
def register(user_in: UserCreate, auth_service: AuthService = Depends(get_auth_service)):
    return auth_service.register(user_in)

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/login", response_model=AuthResponse)
def login(
    login_in: LoginRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"{client_ip}:{login_in.email.lower()}"

    if login_rate_limiter.is_blocked(
        rate_key, LOGIN_MAX_FAILURES, LOGIN_WINDOW_SECONDS
    ):
        raise TooManyRequestsException(
            "Too many failed login attempts. Please try again in a minute."
        )

    try:
        response = auth_service.login(login_in.email, login_in.password)
    except UnauthorizedException:
        # Only failures count toward the lockout.
        login_rate_limiter.record_failure(rate_key, LOGIN_WINDOW_SECONDS)
        raise
    login_rate_limiter.reset(rate_key)
    return response

class RefreshRequest(BaseModel):
    refresh_token: str

@router.post("/refresh", response_model=Token)
def refresh(refresh_in: RefreshRequest, auth_service: AuthService = Depends(get_auth_service)):
    import jwt

    from app.core.config import settings

    try:
        payload = jwt.decode(refresh_in.refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        if user_id is None or token_type != "refresh":
            raise UnauthorizedException()
    except jwt.InvalidTokenError:
        raise UnauthorizedException() from None

    return auth_service.refresh(user_id)


@router.post("/logout", status_code=204)
def logout(current_user = Depends(get_current_active_user)):
    """Stateless logout: access/refresh tokens cannot be revoked server-side,
    so the client discards them. The endpoint exists so clients have an
    explicit logout call and invalid credentials are rejected here."""
    return Response(status_code=204)


@router.post("/change-password", status_code=204)
def change_password(
    payload: ChangePasswordRequest,
    current_user = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    auth_service.change_password(
        current_user, payload.current_password, payload.new_password
    )
    return Response(status_code=204)
