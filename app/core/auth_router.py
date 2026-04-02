import logging

from fastapi import APIRouter, Depends, Request
from app.core.auth_schema import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    AccessTokenResponse,
    UserResponse,
    MessageResponse,
)
from app.core.auth import (
    register_user,
    login_user,
    refresh_access,
    remove_account,
    revoke_token,
    get_current_user,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(req: RegisterRequest):
    """Create a new account."""
    user = register_user(req.email, req.password, req.display_name)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    """Log into existing account → get access + refresh tokens."""
    return login_user(req.email, req.password)


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(req: RefreshRequest):
    """Exchange a refresh token for a new access token."""
    return refresh_access(req.refresh_token)


@router.post("/logout", response_model=MessageResponse)
async def logout(request: Request, user: dict = Depends(get_current_user)):
    """Revoke the current access token."""
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "") if auth.startswith("Bearer ") else ""
    revoke_token(token)
    return {"message": "Logged out"}


@router.get("/me", response_model=UserResponse)
async def me(user: dict = Depends(get_current_user)):
    """Get current user profile."""
    return user


@router.delete("/account", response_model=MessageResponse)
async def delete_account(request: Request, user: dict = Depends(get_current_user)):
    """Permanently delete account."""
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "") if auth.startswith("Bearer ") else ""
    remove_account(user["user_id"], token)
    return {"message": "Account deleted"}