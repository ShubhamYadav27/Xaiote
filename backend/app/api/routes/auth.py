import datetime
import hashlib
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.dependencies.auth import get_current_user
from app.core.security import create_access_token, get_password_hash, verify_password
from app.infrastructure.database.session import get_db
from app.models.company import Company
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import RefreshRequest, UserLogin, UserRegister

router = APIRouter()


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@router.post("/register")
async def register(user_in: UserRegister, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalars().first():
        raise HTTPException(
            status_code=400,
            detail="Email already registered",
        )

    company = Company(
        name=user_in.company_name,
        industry=user_in.industry,
        revenue_range=user_in.revenue_range,
    )
    db.add(company)
    await db.flush()

    user = User(
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        company_id=company.id,
        role="OWNER",
    )
    db.add(user)
    await db.commit()
    return {"data": {"message": "User and company created successfully"}}


@router.post("/login")
async def login(user_in: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    user = result.scalars().first()
    if not user or not verify_password(user_in.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
        )

    access_token = create_access_token(
        {"sub": str(user.id), "company_id": str(user.company_id)}
    )
    raw_refresh_token = str(uuid.uuid4())

    rt_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(raw_refresh_token),
        expires_at=datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(days=7),
    )
    db.add(rt_record)
    await db.commit()

    return {"data": {"access_token": access_token, "refresh_token": raw_refresh_token}}


@router.post("/refresh")
async def refresh(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    hashed_rt = hash_token(req.refresh_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == hashed_rt)
    )
    rt_record = result.scalars().first()

    if not rt_record or rt_record.expires_at < datetime.datetime.now(
        datetime.timezone.utc
    ):
        raise HTTPException(
            status_code=401,
            detail="Refresh token is invalid or expired",
        )

    result_user = await db.execute(select(User).where(User.id == rt_record.user_id))
    user = result_user.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User no longer exists")

    # Revoke old token by deleting it (rotation)
    await db.delete(rt_record)

    access_token = create_access_token(
        {"sub": str(user.id), "company_id": str(user.company_id)}
    )
    new_raw_refresh_token = str(uuid.uuid4())

    new_rt_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(new_raw_refresh_token),
        expires_at=datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(days=7),
    )
    db.add(new_rt_record)
    await db.commit()

    return {
        "data": {"access_token": access_token, "refresh_token": new_raw_refresh_token}
    }


@router.post("/logout")
async def logout(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    hashed_rt = hash_token(req.refresh_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == hashed_rt)
    )
    rt_record = result.scalars().first()
    if rt_record:
        await db.delete(rt_record)
        await db.commit()
    return {"data": {"message": "Logged out"}}


@router.get("/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "data": {
            "email": current_user.email,
            "full_name": current_user.full_name,
            "company_id": current_user.company_id,
        }
    }
