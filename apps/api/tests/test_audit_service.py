from app.services.audit import _sanitize


def test_audit_payload_redacts_sensitive_values() -> None:
    payload = _sanitize(
        {
            "username": "analyst",
            "password": "secret",
            "nested": {"access_token": "token", "safe": True},
        }
    )
    assert payload == {
        "username": "analyst",
        "password": "[REDACTED]",
        "nested": {"access_token": "[REDACTED]", "safe": True},
    }
