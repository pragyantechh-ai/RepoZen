import json
import logging
from datetime import datetime
from typing import Optional

import redis

logger = logging.getLogger(__name__)

_pool: Optional[redis.ConnectionPool] = None
_client: Optional[redis.Redis] = None

# ── Key prefixes ──────────────────────────────────────────────────
USER_KEY = "user:{}"             # user:<user_id>  → hash
EMAIL_INDEX = "email_idx:{}"     # email_idx:<email> → user_id
TOKEN_BLOCKLIST = "blocklist:{}" # blocklist:<jti>  → "1"
USER_COUNTER = "global:user_counter"


def get_redis(
    host: str = "127.0.0.1",
    port: int = 6379,
    db: int = 0,
    decode_responses: bool = True,
) -> redis.Redis:
    """Return a singleton Redis client (lazy-init, thread-safe pool)."""
    global _pool, _client
    if _client is None:
        _pool = redis.ConnectionPool(
            host=host,
            port=port,
            db=db,
            decode_responses=decode_responses,
            max_connections=20,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
        )
        _client = redis.Redis(connection_pool=_pool)
        # Verify connectivity
        _client.ping()
        logger.info("[Redis] Connected to %s:%s db=%s", host, port, db)
    return _client


def close_redis() -> None:
    """Gracefully close the pool (call on app shutdown)."""
    global _pool, _client
    if _client:
        _client.close()
        _client = None
    if _pool:
        _pool.disconnect()
        _pool = None
    logger.info("[Redis] Connection closed")


# ═════════════════════════════════════════════════════════════════════
#  User CRUD helpers
# ═════════════════════════════════════════════════════════════════════

def _next_user_id() -> str:
    r = get_redis()
    seq = r.incr(USER_COUNTER)
    return f"u_{seq}"


def create_user(email: str, hashed_password: str, display_name: str) -> dict:
    """Atomically create a user + email-index. Returns user dict."""
    r = get_redis()
    email_lower = email.lower().strip()

    # Check uniqueness
    if r.exists(EMAIL_INDEX.format(email_lower)):
        raise ValueError("Email already registered")

    uid = _next_user_id()
    now = datetime.utcnow().isoformat()

    user_data = {
        "user_id": uid,
        "email": email_lower,
        "display_name": display_name,
        "hashed_password": hashed_password,
        "created_at": now,
        "updated_at": now,
    }

    pipe = r.pipeline(transaction=True)
    pipe.hset(USER_KEY.format(uid), mapping=user_data)
    pipe.set(EMAIL_INDEX.format(email_lower), uid)
    pipe.execute()

    logger.info("[Redis] User created: %s (%s)", uid, email_lower)
    return user_data


def get_user_by_id(user_id: str) -> Optional[dict]:
    r = get_redis()
    data = r.hgetall(USER_KEY.format(user_id))
    return data if data else None


def get_user_by_email(email: str) -> Optional[dict]:
    r = get_redis()
    email_lower = email.lower().strip()
    uid = r.get(EMAIL_INDEX.format(email_lower))
    if not uid:
        return None
    return get_user_by_id(uid)


def delete_user(user_id: str) -> bool:
    """Delete user hash + email index. Returns True if deleted."""
    r = get_redis()
    user = get_user_by_id(user_id)
    if not user:
        return False

    pipe = r.pipeline(transaction=True)
    pipe.delete(USER_KEY.format(user_id))
    pipe.delete(EMAIL_INDEX.format(user["email"]))
    pipe.execute()

    logger.info("[Redis] User deleted: %s", user_id)
    return True


def update_user(user_id: str, fields: dict) -> Optional[dict]:
    """Partial update. Returns updated user dict."""
    r = get_redis()
    key = USER_KEY.format(user_id)
    if not r.exists(key):
        return None

    fields["updated_at"] = datetime.utcnow().isoformat()
    r.hset(key, mapping=fields)
    return r.hgetall(key)


# ═════════════════════════════════════════════════════════════════════
#  Token blocklist (for logout / token revocation)
# ═════════════════════════════════════════════════════════════════════

def blocklist_token(jti: str, ttl_seconds: int) -> None:
    """Add a JWT id to the blocklist with matching TTL."""
    r = get_redis()
    r.setex(TOKEN_BLOCKLIST.format(jti), ttl_seconds, "1")


def is_token_blocklisted(jti: str) -> bool:
    r = get_redis()
    return r.exists(TOKEN_BLOCKLIST.format(jti)) == 1