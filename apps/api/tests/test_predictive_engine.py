import pytest

from app.services.predictive import (
    canopy_trend,
    flood_probability,
    heat_trend,
    vulnerability_scenario,
)


def test_heat_trend_projects_forward() -> None:
    result = heat_trend([30.0, 31.0, 32.0], 2)
    assert result["forecast"] == [{"period": 1, "value": 33.0}, {"period": 2, "value": 34.0}]


def test_canopy_is_bounded() -> None:
    result = canopy_trend([98.0, 99.0, 100.0], 2)
    assert all(0 <= point["value"] <= 100 for point in result["forecast"])


def test_flood_probability_uses_configurable_coefficients() -> None:
    result = flood_probability({"rainfall": 2.0}, {"intercept": -1.0, "rainfall": 1.0})
    assert 0.73 < result["probability"] < 0.74


def test_vulnerability_scenario_reports_delta() -> None:
    result = vulnerability_scenario(
        {"exposure": 0.5, "capacity": 0.5}, {"exposure": 1, "capacity": -1}, {"exposure": 0.2}
    )
    assert result["delta"] > 0


def test_trend_requires_history() -> None:
    with pytest.raises(ValueError):
        heat_trend([30.0], 2)
