"""User management service — CRUD, role assignment, status toggle.

Zero FastAPI imports. All business logic operates on DB sessions + plain objects.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Role, User, UserStatus
from app.models.audit_log import AuditLog
from app.services.auth_service import hash_password


async def list_users(
    db: AsyncSession, skip: int = 0, limit: int = 50
) -> list[User]:
    """Return paginated list of all users."""
    result = await db.execute(
        select(User).offset(skip).limit(limit).order_by(User.created_at.desc())
    )
    return list(result.scalars().all())


async def create_user(
    db: AsyncSession,
    email: str,
    username: str,
    password: str,
    full_name: str | None = None,
    role: str = "VIEWER",
) -> User:
    """Admin creates a user with a specified role."""
    # Check duplicates
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise ValueError("Email already registered")

    existing = await db.execute(select(User).where(User.username == username))
    if existing.scalar_one_or_none():
        raise ValueError("Username already taken")

    user = User(
        email=email,
        username=username,
        password_hash=hash_password(password),
        full_name=full_name,
        role=Role(role),
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def update_user_role(db: AsyncSession, user_id: int, new_role: str, performer_id: int) -> User:
    """Change a user's role. Raises ValueError if user not found."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise ValueError("User not found")
    user.role = Role(new_role)
    
    # Audit trail
    db.add(AuditLog(
        user_id=performer_id,
        action="UPDATE_ROLE",
        entity="User",
        entity_id=user.id,
        details=f"User role changed to {new_role}"
    ))

    await db.flush()
    await db.refresh(user)
    return user


async def toggle_user_status(db: AsyncSession, user_id: int, new_status: str, performer_id: int) -> User:
    """Activate or deactivate a user. Raises ValueError if user not found."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise ValueError("User not found")
    user.status = UserStatus(new_status)
    
    # Audit trail
    db.add(AuditLog(
        user_id=performer_id,
        action="UPDATE_STATUS",
        entity="User",
        entity_id=user.id,
        details=f"User status changed to {new_status}"
    ))

    await db.flush()
    await db.refresh(user)
    return user
