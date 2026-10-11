from fastapi import Depends, HTTPException, status

from app.dependencies.auth import get_current_active_user
from app.models.user import User


def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    roles = []
    for r in current_user.user_roles:
        if hasattr(r, "role"):
            roles.append(str(r.role).lower())
        elif hasattr(r, "role_name"):
            roles.append(str(r.role_name).lower())
    if "admin" not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


def require_seller_or_admin(current_user: User = Depends(get_current_active_user)) -> User:
    roles = []
    for r in current_user.user_roles:
        if hasattr(r, "role"):
            roles.append(str(r.role).lower())
        elif hasattr(r, "role_name"):
            roles.append(str(r.role_name).lower())
    if "admin" not in roles and "seller" not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Seller or Admin access required")
    return current_user
