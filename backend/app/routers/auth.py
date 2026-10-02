from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas.user import UserCreate, AuthResponse, Token
from app.services.auth_service import AuthService
from app.repositories.user_repo import UserRepository
from app.database.session import get_db
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])

def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(UserRepository(db))

@router.post("/register", response_model=AuthResponse)
def register(user_in: UserCreate, auth_service: AuthService = Depends(get_auth_service)):
    return auth_service.register(user_in)

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/login", response_model=AuthResponse)
def login(login_in: LoginRequest, auth_service: AuthService = Depends(get_auth_service)):
    return auth_service.login(login_in.email, login_in.password)

class RefreshRequest(BaseModel):
    refresh_token: str

@router.post("/refresh", response_model=Token)
def refresh(refresh_in: RefreshRequest, auth_service: AuthService = Depends(get_auth_service)):
    from jose import jwt, JWTError
    from app.core.config import settings
    from app.core.exceptions import UnauthorizedException
    
    try:
        payload = jwt.decode(refresh_in.refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        if user_id is None or token_type != "refresh":
            raise UnauthorizedException()
    except JWTError:
        raise UnauthorizedException()
        
    return auth_service.refresh(user_id)
