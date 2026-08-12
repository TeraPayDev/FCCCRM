import pytest

from app.services import public_data


def test_open_meteo_normalizes_current_and_hourly(monkeypatch: pytest.MonkeyPatch) -> None:
    public_data._CACHE.clear()
    monkeypatch.setattr(
        public_data,
        "_request_json",
        lambda *args, **kwargs: {
            "current": {"temperature_2m": 30.5, "relative_humidity_2m": 70},
            "hourly": {
                "time": ["2026-08-11T12:00"],
                "temperature_2m": [30.5],
                "relative_humidity_2m": [70],
                "precipitation": [1.2],
                "rain": [1.0],
            },
        },
    )
    result = public_data.open_meteo_freetown()
    assert result["record_count"] == 1
    hourly = result["hourly"]
    assert isinstance(hourly, list)
    first = hourly[0]
    assert isinstance(first, dict)
    assert first["precipitation_mm"] == 1.2


def test_world_bank_uses_latest_numeric_value(monkeypatch: pytest.MonkeyPatch) -> None:
    public_data._CACHE.clear()
    monkeypatch.setattr(
        public_data,
        "_request_json",
        lambda *args, **kwargs: [
            {},
            [{"date": "2025", "value": None}, {"date": "2024", "value": 42.0}],
        ],
    )
    result = public_data.world_bank_sierra_leone()
    assert result["record_count"] == 4
    records = result["records"]
    assert isinstance(records, list)
    assert all(isinstance(item, dict) and item["value"] == 42.0 for item in records)
