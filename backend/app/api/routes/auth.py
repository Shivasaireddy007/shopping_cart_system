from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, SessionDep
from app.core.config import get_settings
from app.core.security import create_token, decode_token, hash_password, verify_password
from app.models import User
from app.schemas.auth import LoginIn, RefreshIn, RegisterIn, TokenPair, UserOut

router = APIRouter(prefix="/auth", tags=["Auth"])


def _tokens(user_id: int) -> TokenPair:
    return TokenPair(
        access_token=create_token(user_id, "access"),
        refresh_token=create_token(user_id, "refresh"),
        expires_in=get_settings().access_token_minutes * 60,
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(data: RegisterIn, session: SessionDep) -> TokenPair:
    """Create a customer account and get a token pair."""
    user = User(email=data.email.lower(), name=data.name, password_hash=hash_password(data.password))
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.") from None
    return _tokens(user.id)


@router.post("/login")
async def login(data: LoginIn, session: SessionDep) -> TokenPair:
    """Log in with email and password."""
    user = await session.scalar(select(User).where(User.email == data.email.lower()))
    if user is None or not verify_password(user.password_hash, data.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password.")
    return _tokens(user.id)


@router.post("/refresh")
async def refresh(data: RefreshIn, session: SessionDep) -> TokenPair:
    """Exchange a refresh token for a new token pair."""
    user_id = decode_token(data.refresh_token, "refresh")
    if user_id is None or await session.get(User, user_id) is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token.")
    return _tokens(user_id)


@router.get("/me")
async def me(user: CurrentUser) -> UserOut:
    """Get the logged-in user."""
    return UserOut.model_validate(user)
