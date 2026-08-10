from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt

from app.core.config import get_settings

TokenType = Literal["access", "refresh"]


@dataclass(frozen=True)
class TokenClaims:
    subject: uuid.UUID
    token_type: TokenType
    token_version: int
    expires_at: datetime
    token_id: uuid.UUID


class TokenError(ValueError):
    pass


def create_token(
    *,
    subject: uuid.UUID,
    token_type: TokenType,
    token_version: int,
    lifetime: timedelta,
) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(subject),
        "typ": token_type,
        "ver": token_version,
        "iat": now,
        "exp": now + lifetime,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(
        payload,
        settings.auth_jwt_secret.get_secret_value(),
        algorithm="HS256",
    )


def decode_token(token: str, *, expected_type: TokenType) -> TokenClaims:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.auth_jwt_secret.get_secret_value(),
            algorithms=["HS256"],
            options={"require": ["sub", "typ", "ver", "iat", "exp", "jti"]},
        )
        token_type = payload["typ"]
        if token_type != expected_type:
            raise TokenError("Unexpected token type.")
        return TokenClaims(
            subject=uuid.UUID(payload["sub"]),
            token_type=token_type,
            token_version=int(payload["ver"]),
            expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
            token_id=uuid.UUID(payload["jti"]),
        )
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, TokenError):
            raise
        raise TokenError("Invalid or expired token.") from exc
