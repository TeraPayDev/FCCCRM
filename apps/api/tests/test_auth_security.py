import uuid
from datetime import timedelta

import pytest

from app.security.passwords import hash_password, verify_password
from app.security.tokens import TokenError, create_token, decode_token


def test_password_hashing_round_trip() -> None:
    encoded = hash_password("A-strong-test-password-123")
    assert encoded != "A-strong-test-password-123"
    assert verify_password("A-strong-test-password-123", encoded)
    assert not verify_password("wrong-password", encoded)


def test_token_type_is_enforced() -> None:
    token = create_token(
        subject=uuid.uuid4(),
        token_type="refresh",
        token_version=0,
        lifetime=timedelta(minutes=5),
    )
    with pytest.raises(TokenError):
        decode_token(token, expected_type="access")


def test_expired_token_is_rejected() -> None:
    token = create_token(
        subject=uuid.uuid4(),
        token_type="access",
        token_version=0,
        lifetime=timedelta(seconds=-1),
    )
    with pytest.raises(TokenError):
        decode_token(token, expected_type="access")
