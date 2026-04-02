"""Role-Based Access Control dependency using FastAPI Depends()."""

from fastapi import Depends, HTTPException, status

from app.middleware.auth import get_current_user
from app.models.user import User


def require_role(*allowed_roles: str):
    """
    Factory that returns a dependency checking the user's role.

    Usage:
        @router.post("/", dependencies=[Depends(require_role("ANALYST", "ADMIN"))])
    """

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.value not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role.value}' is not permitted. "
                       f"Required: {', '.join(allowed_roles)}",
            )
        return current_user

    return role_checker
