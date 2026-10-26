from fastapi import Depends, HTTPException, status

from app.dependencies.auth import get_current_active_user
from app.models.user import User


def collect_role_names(current_user: User) -> list[str]:
    """All role names that apply to a user, lower-cased.

    `users.role` is the authoritative single primary role column (see
    `app/models/role.py`); the `user_roles` table is the normalized mapping of
    it. `UserRole.role` is a *relationship* to a `Role` row, so the name has to
    be read from `r.role.name` — stringifying the relationship object yields
    its repr (e.g. `<app.models.role.Role object at 0x...>`), which never
    matches a role name and silently denies every privileged request.
    """
    roles: list[str] = []

    primary = getattr(current_user, "role", None)
    if primary:
        roles.append(str(primary).lower())

    for user_role in getattr(current_user, "user_roles", None) or []:
        name = getattr(user_role, "role_name", None)
        if name is None:
            role_obj = getattr(user_role, "role", None)
            name = getattr(role_obj, "name", None)
        if name:
            roles.append(str(name).lower())

    return roles


def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    if "admin" not in collect_role_names(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return current_user


def require_seller_or_admin(
    current_user: User = Depends(get_current_active_user),
) -> User:
    roles = collect_role_names(current_user)
    if "admin" not in roles and "seller" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seller or Admin access required",
        )
    return current_user
