from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.auth import (
    get_current_user,
    hash_password,
    verify_password,
    create_access_token,
)
from app.models.user import User
from app.schemas.user import ChangePasswordRequest, UserCreate, UserResponse, LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/create", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check email not already taken
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=payload.email,
        password=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive")

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user=user)


# @router.patch("/change-password", status_code=status.HTTP_200_OK)
# async def change_password(
#     payload: ChangePasswordRequest,
#     db: AsyncSession = Depends(get_db),
#     current_user: User = Depends(get_current_user),
# ):
#     if not verify_password(payload.current_password, current_user.password):
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Current password is incorrect",
#         )
#     if payload.current_password == payload.new_password:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="New password must be different from current password",
#         )

#     current_user.password = hash_password(payload.new_password)
#     await db.commit()
#     return {"detail": "Password updated successfully"}

@router.patch("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    payload: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(payload.current_password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )
    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password",
        )

    user.password = hash_password(payload.new_password)
    await db.commit()
    return {"detail": "Password updated successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
