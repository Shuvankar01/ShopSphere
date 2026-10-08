from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    UnauthorizedException,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from app.repositories.user_repo import UserRepository
from app.schemas.user import AuthResponse, Token, UserCreate


class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def register(self, user_in: UserCreate) -> AuthResponse:
        existing = self.user_repo.get_by_email(user_in.email)
        if existing:
            raise ConflictException("User with this email already exists")

        user = self.user_repo.create(user_in)
        access_token = create_access_token(subject=user.id)
        refresh_token = create_refresh_token(subject=user.id)

        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=user
        )

    def login(self, email: str, password: str) -> AuthResponse:
        user = self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise UnauthorizedException("Incorrect email or password")
        if not user.is_active:
            raise UnauthorizedException("Inactive user")

        access_token = create_access_token(subject=user.id)
        refresh_token = create_refresh_token(subject=user.id)

        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=user
        )

    def refresh(self, user_id: str) -> Token:
        user = self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
             raise UnauthorizedException("Invalid user")

        access_token = create_access_token(subject=user.id)
        # Normally we'd rotate refresh tokens, but keeping it simple for frontend expectations

        return Token(
            access_token=access_token,
            token_type="bearer"
        )

    def change_password(
        self, user, current_password: str, new_password: str
    ) -> None:
        """Verify the current password then set the new one.

        Tokens remain valid until expiry (stateless JWT — see README notes).
        """
        if not verify_password(current_password, user.hashed_password):
            raise UnauthorizedException("Current password is incorrect")
        if current_password == new_password:
            raise BadRequestException(
                "New password must differ from the current password"
            )
        user.hashed_password = get_password_hash(new_password)
        self.user_repo.db.commit()
