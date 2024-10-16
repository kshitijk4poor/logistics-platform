from fastapi import HTTPException
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.schemas.user import UserCreate, UserResponse

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def create_user_service(user_data: UserCreate, db: AsyncSession) -> UserResponse:
    hashed_password = pwd_context.hash(user_data.password)
    new_user = User(
        email=user_data.email, hashed_password=hashed_password, name=user_data.name
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


async def get_user_service(user_id: int, db: AsyncSession) -> UserResponse:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
