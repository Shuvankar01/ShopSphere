from app.repositories.user_repo import UserRepository
from app.schemas.user import UserUpdate
from app.models.user import User

class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def update_profile(self, current_user: User, user_in: UserUpdate) -> User:
        return self.user_repo.update(current_user, user_in)
