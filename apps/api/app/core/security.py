import hashlib
from datetime import datetime
from typing import Any
from uuid import UUID

import jwt
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

from app.core.config import Settings
from app.core.timeutil import utcnow

JWT_ALGORITHM = "HS256"

_hasher = PasswordHash.recommended()
_dummy_hash: str | None = None


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _hasher.verify(password, hashed)
    except UnknownHashError:
        return False


def dummy_verify(password: str) -> None:
    """Burn comparable CPU time for unknown users to blunt user enumeration by timing."""
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = _hasher.hash("lancast-dummy-password")
    _hasher.verify(password, _dummy_hash)


def issue_token(user_id: UUID, session_id: UUID, expires_at: datetime, settings: Settings) -> str:
    claims: dict[str, Any] = {
        "sub": str(user_id),
        "jti": str(session_id),
        "iat": int(utcnow().timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    return jwt.encode(claims, settings.auth_secret_key, algorithm=JWT_ALGORITHM)


def decode_token(token: str, settings: Settings) -> dict[str, Any]:
    return jwt.decode(
        token,
        settings.auth_secret_key,
        algorithms=[JWT_ALGORITHM],
        options={"require": ["exp", "sub", "jti"]},
    )


def email_fingerprint(email: str) -> str:
    """Short digest so audit logs can correlate attempts without storing raw emails."""
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()[:12]
