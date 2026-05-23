"""
Authentication service: handles user registration, login,
password hashing, and token generation.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext
from fastapi import HTTPException, status

from app.models.user import User
from app.schemas.auth import UserRegisterRequest, UserLoginRequest, TokenResponse
from app.core.security import create_access_token, create_refresh_token, verify_token


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Encapsulates all authentication business logic."""

    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)

    @staticmethod
    async def register(db: AsyncSession, data: UserRegisterRequest) -> TokenResponse:
        """
        Register a new user.
        - Checks for duplicate email
        - Hashes password
        - Creates user record
        - Returns JWT tokens
        """
        # Check duplicate
        stmt = select(User).where(User.email == data.email)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists.",
            )

        # Create user
        user = User(
            email=data.email,
            password_hash=AuthService.hash_password(data.password),
            full_name=data.full_name,
        )
        db.add(user)
        await db.flush()

        # Generate tokens
        token_data = {"sub": str(user.id), "email": user.email}
        return TokenResponse(
            access_token=create_access_token(token_data),
            refresh_token=create_refresh_token(token_data),
        )

    @staticmethod
    async def login(db: AsyncSession, data: UserLoginRequest) -> TokenResponse:
        """
        Authenticate a user with email + password.
        Returns JWT tokens on success.
        """
        stmt = select(User).where(User.email == data.email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not AuthService.verify_password(data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated.",
            )

        token_data = {"sub": str(user.id), "email": user.email}
        return TokenResponse(
            access_token=create_access_token(token_data),
            refresh_token=create_refresh_token(token_data),
        )

    @staticmethod
    async def refresh(db: AsyncSession, refresh_token: str) -> TokenResponse:
        """
        Issue new access + refresh tokens using a valid refresh token.
        """
        payload = verify_token(refresh_token, expected_type="refresh")
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token.",
            )

        user_id = payload.get("sub")
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or deactivated.",
            )

        token_data = {"sub": str(user.id), "email": user.email}
        return TokenResponse(
            access_token=create_access_token(token_data),
            refresh_token=create_refresh_token(token_data),
        )
