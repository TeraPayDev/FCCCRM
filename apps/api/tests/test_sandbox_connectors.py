from app.services.connectors import sandbox_pull


def test_slmet_sandbox_connector_returns_deterministic_sample() -> None:
    result = sandbox_pull("SL-Met")
    assert result["mode"] == "sandbox"
    assert result["record_count"] == 1


def test_unknown_connector_is_safe_and_empty() -> None:
    result = sandbox_pull("Unknown Institution")
    assert result["record_count"] == 0
