from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas.user import UserResponse, UserUpdate
from app.models.user import User
from app.services.user_service import UserService
from app.repositories.user_repo import UserRepository
from app.database.session import get_db
from app.dependencies.auth import get_current_active_user

router = APIRouter(prefix="/users", tags=["users"])

def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(UserRepository(db))

@router.get("/profile", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_active_user)):
    return current_user

@router.put("/profile", response_model=UserResponse)
def update_profile(
    user_in: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):
    return user_service.update_profile(current_user, user_in)
