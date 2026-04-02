import logging
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.db.redis_client import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    delete_user,
    blocklist_token,
    is_token_blocklisted,
)

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────
SECRET_KEY = "repozen-change-me-in-production-use-env-var"  # TODO: move to env
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS = 30

bearer_scheme = HTTPBearer(auto_error=False)


# ═════════════════════════════════════════════════════════════════════
#  Password helpers  (bcrypt directly, no passlib)
# ═════════════════════════════════════════════════════════════════════

def hash_password(plain: str) -> str:
    """Pre-hash with SHA-256 (to bypass 72-byte limit), then bcrypt."""
    pre = hashlib.sha256(plain.encode("utf-8")).hexdigest().encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pre, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    pre = hashlib.sha256(plain.encode("utf-8")).hexdigest().encode("utf-8")
    try:
        return bcrypt.checkpw(pre, hashed.encode("utf-8"))
    except Exception:
        return False


# ═════════════════════════════════════════════════════════════════════
#  JWT helpers
# ═════════════════════════════════════════════════════════════════════

def _create_token(data: dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    jti = uuid.uuid4().hex
    to_encode.update({
        "exp": datetime.utcnow() + expires_delta,
        "iat": datetime.utcnow(),
        "jti": jti,
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(user_id: str) -> str:
    return _create_token(
        {"sub": user_id, "type": "access"},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: str) -> str:
    return _create_token(
        {"sub": user_id, "type": "refresh"},
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> dict:
    """Decode + verify. Raises HTTPException on failure."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
        )
    jti = payload.get("jti", "")
    if is_token_blocklisted(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
        )
    return payload


def revoke_token(token: str) -> None:
    """Blocklist a token by its jti."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        jti = payload.get("jti", "")
        exp = payload.get("exp", 0)
        ttl = max(int(exp - datetime.utcnow().timestamp()), 1)
        blocklist_token(jti, ttl)
    except JWTError:
        pass  # already invalid


# ═════════════════════════════════════════════════════════════════════
#  Auth dependency for FastAPI routes
# ═════════════════════════════════════════════════════════════════════

async def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict:
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    payload = decode_token(creds.credentials)
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )
    user = get_user_by_id(payload["sub"])
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
        )
    return user


# ═════════════════════════════════════════════════════════════════════
#  High-level operations (called by router)
# ═════════════════════════════════════════════════════════════════════

def register_user(email: str, password: str, display_name: str) -> dict:
    """Create account → return user dict (without password)."""
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters",
        )
    hashed = hash_password(password)
    try:
        user = create_user(email, hashed, display_name)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    user.pop("hashed_password", None)
    return user


def login_user(email: str, password: str) -> dict:
    """Verify creds → return tokens + user."""
    user = get_user_by_email(email)
    if not user or not verify_password(password, user.get("hashed_password", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    safe_user = {k: v for k, v in user.items() if k != "hashed_password"}
    return {
        "access_token": create_access_token(user["user_id"]),
        "refresh_token": create_refresh_token(user["user_id"]),
        "user": safe_user,
    }


def refresh_access(refresh_token_str: str) -> dict:
    """Issue a new access token from a valid refresh token."""
    payload = decode_token(refresh_token_str)
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not a refresh token",
        )
    user = get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
        )
    return {
        "access_token": create_access_token(user["user_id"]),
    }


def remove_account(user_id: str, token: str) -> None:
    """Delete user and revoke the current token."""
    ok = delete_user(user_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    revoke_token(token)