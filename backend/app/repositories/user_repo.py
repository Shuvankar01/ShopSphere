from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.role import Role, UserRole
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate

ROLE_DESCRIPTIONS = {
    "customer": "Shop and place orders",
    "seller": "Manage own products and inventory",
    "admin": "Full administrative access",
}


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str) -> User | None:
        return self.db.query(User).filter(User.email == email).first()

    def get_by_id(self, id: str) -> User | None:
        return self.db.query(User).filter(User.id == id).first()

    def get_all(self) -> list[User]:
        return self.db.query(User).all()

    def get_total_count(self) -> int:
        return self.db.query(User).count()

    def _get_or_create_role(self, role_name: str) -> Role:
        role = self.db.query(Role).filter(Role.name == role_name).first()
        if role is not None:
            return role
        role = Role(name=role_name, description=ROLE_DESCRIPTIONS.get(role_name))
        self.db.add(role)
        try:
            self.db.flush()
        except IntegrityError:
            # Another request created the same role concurrently.
            self.db.rollback()
            role = self.db.query(Role).filter(Role.name == role_name).first()
            if role is None:
                raise
        return role

    def create(self, user_in: UserCreate) -> User:
        role_name = user_in.role or "customer"
        # Create the normalized role mapping first (before any rollback risk
        # to the user insert). `users.role` stays the primary role used by
        # authorization; `user_roles` mirrors it.
        role = self._get_or_create_role(role_name)

        hashed_password = get_password_hash(user_in.password)
        db_user = User(
            full_name=user_in.full_name,
            email=user_in.email,
            hashed_password=hashed_password,
            role=role_name
        )
        self.db.add(db_user)
        self.db.flush()
        self.db.add(UserRole(user_id=db_user.id, role_id=role.id))
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def update(self, db_user: User, user_in: UserUpdate) -> User:
        update_data = user_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_user, field, value)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user
