import pytest

from app.services.predictive import (
    canopy_trend,
    flood_probability,
    heat_trend,
    vulnerability_scenario,
)


def test_heat_trend_projects_forward() -> None:
    result = heat_trend([30.0, 31.0, 32.0], 2)
    forecast = result["forecast"]
    assert isinstance(forecast, list)
    assert [point["value"] for point in forecast if isinstance(point, dict)] == [33.0, 34.0]
    assert all(
        isinstance(point, dict)
        and float(point["lower"]) <= float(point["value"]) <= float(point["upper"])
        for point in forecast
    )
    metrics = result["metrics"]
    assert isinstance(metrics, dict)
    assert metrics["observations"] == 3
    assert result["trend_direction"] == "WARMING"


def test_canopy_is_bounded() -> None:
    result = canopy_trend([98.0, 99.0, 100.0], 2)
    forecast = result["forecast"]
    assert isinstance(forecast, list)
    assert all(isinstance(point, dict) and 0 <= float(point["value"]) <= 100 for point in forecast)


def test_flood_probability_uses_configurable_coefficients() -> None:
    result = flood_probability({"rainfall": 2.0}, {"intercept": -1.0, "rainfall": 1.0})
    probability = result["probability"]
    assert isinstance(probability, int | float)
    assert 0.73 < probability < 0.74


def test_vulnerability_scenario_reports_delta() -> None:
    result = vulnerability_scenario(
        {"exposure": 0.5, "capacity": 0.5}, {"exposure": 1, "capacity": -1}, {"exposure": 0.2}
    )
    delta = result["delta"]
    assert isinstance(delta, int | float)
    assert delta > 0


def test_trend_requires_history() -> None:
    with pytest.raises(ValueError):
        heat_trend([30.0], 2)
