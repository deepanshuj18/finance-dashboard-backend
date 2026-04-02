"""User management routes — all require ADMIN role."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.rbac import require_role
from app.models.user import User
from app.schemas.user import RoleUpdate, StatusUpdate, UserCreate, UserOut
from app.services.user_service import (
    create_user,
    list_users,
    toggle_user_status,
    update_user_role,
)

router = APIRouter(prefix="/users", tags=["User Management"])


@router.get(
    "/",
    response_model=list[UserOut],
    dependencies=[Depends(require_role("ADMIN"))],
    summary="List all users (Admin only)",
)
async def get_users(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    users = await list_users(db, skip=skip, limit=limit)
    return users


@router.post(
    "/",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("ADMIN"))],
    summary="Create a user with role (Admin only)",
)
async def create_new_user(body: UserCreate, db: AsyncSession = Depends(get_db)):
    try:
        user = await create_user(
            db,
            email=body.email,
            username=body.username,
            password=body.password,
            full_name=body.full_name,
            role=body.role,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return user


@router.patch(
    "/{user_id}/role",
    response_model=UserOut,
    summary="Assign role to user (Admin only)",
)
async def update_role(
    user_id: int, 
    body: RoleUpdate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN")),
):
    try:
        user = await update_user_role(db, user_id, body.role, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return user


@router.patch(
    "/{user_id}/status",
    response_model=UserOut,
    summary="Activate / Deactivate user (Admin only)",
)
async def update_status(
    user_id: int, 
    body: StatusUpdate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN")),
):
    try:
        user = await toggle_user_status(db, user_id, body.status, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return user
