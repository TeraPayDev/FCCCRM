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


def test_nasa_power_suppresses_missing_value_sentinel(monkeypatch: pytest.MonkeyPatch) -> None:
    public_data._CACHE.clear()
    monkeypatch.setattr(
        public_data,
        "_request_json",
        lambda *args, **kwargs: {
            "properties": {
                "parameter": {
                    "T2M": {"20260811": -999},
                    "RH2M": {"20260811": 81.0},
                    "PRECTOTCORR": {"20260811": -999},
                    "PS": {"20260811": 101.2},
                    "WS10M": {"20260811": 2.1},
                }
            }
        },
    )
    result = public_data.nasa_power_freetown()
    records = result["records"]
    assert isinstance(records, list)
    first = records[0]
    assert isinstance(first, dict)
    assert first["temperature_c"] is None
    assert first["precipitation_mm"] is None
    assert first["humidity_pct"] == 81.0


def test_open_meteo_grid_builds_real_spatial_features(monkeypatch: pytest.MonkeyPatch) -> None:
    public_data._CACHE.clear()
    monkeypatch.setattr(
        public_data,
        "_request_json",
        lambda *args, **kwargs: {
            "current": {
                "time": "2026-08-12T12:00",
                "temperature_2m": 29.0,
                "relative_humidity_2m": 78,
                "precipitation": 0.5,
                "rain": 0.4,
            }
        },
    )
    result = public_data.open_meteo_freetown_grid()
    assert result["record_count"] == 12
    features = result["features"]
    assert isinstance(features, list)
    first = features[0]
    assert isinstance(first, dict)
    properties = first["properties"]
    assert isinstance(properties, dict)
    assert properties["temperature_c"] == 29.0


def test_world_bank_climate_resources_are_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    public_data._CACHE.clear()
    monkeypatch.setattr(
        public_data,
        "_request_json",
        lambda *args, **kwargs: {
            "documents": {
                "D1": {
                    "id": "D1",
                    "display_title": "Urban climate resilience in coastal cities",
                    "docty": "Policy Research Working Paper",
                    "docdt": "2026-01-10",
                    "authr": "World Bank",
                    "pdfurl": "https://documents.worldbank.org/example.pdf",
                }
            }
        },
    )
    result = public_data.world_bank_climate_resources()
    assert result["record_count"] == 1
    records = result["records"]
    assert isinstance(records, list)
    record = records[0]
    assert isinstance(record, dict)
    assert record["organisation"] == "World Bank"
    assert record["title"] == "Urban climate resilience in coastal cities"
    assert record["url"] == "https://documents.worldbank.org/example.pdf"
