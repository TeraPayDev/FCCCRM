from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import fmean


@dataclass(frozen=True)
class ForecastPoint:
    period: int
    value: float


def _linear_forecast(values: list[float], periods: int) -> list[ForecastPoint]:
    if len(values) < 2:
        raise ValueError("At least two observations are required for a trend forecast.")
    if periods < 1 or periods > 60:
        raise ValueError("Forecast periods must be between 1 and 60.")
    n = len(values)
    xs = list(range(n))
    xbar = fmean(xs)
    ybar = fmean(values)
    denominator = sum((x - xbar) ** 2 for x in xs)
    slope = sum((x - xbar) * (y - ybar) for x, y in zip(xs, values, strict=True)) / denominator
    intercept = ybar - slope * xbar
    return [ForecastPoint(i + 1, intercept + slope * (n + i)) for i in range(periods)]


def heat_trend(values: list[float], periods: int = 7) -> dict[str, object]:
    points = _linear_forecast(values, periods)
    return {
        "engine": "linear-trend-v1",
        "domain": "heat",
        "forecast": [{"period": p.period, "value": round(p.value, 3)} for p in points],
        "warning": "Engineering baseline only; operational thresholds require an approved methodology.",
    }


def canopy_trend(values: list[float], periods: int = 4) -> dict[str, object]:
    points = _linear_forecast(values, periods)
    return {
        "engine": "linear-trend-v1",
        "domain": "canopy",
        "forecast": [
            {"period": p.period, "value": round(max(0.0, min(100.0, p.value)), 3)} for p in points
        ],
        "warning": "Trend projection is bounded to 0-100%; field/remote-sensing validation is required.",
    }


def flood_probability(
    features: dict[str, float], coefficients: dict[str, float]
) -> dict[str, object]:
    if not features:
        raise ValueError("At least one flood feature is required.")
    intercept = float(coefficients.get("intercept", 0.0))
    score = intercept
    used: dict[str, float] = {}
    for name, value in features.items():
        coefficient = float(coefficients.get(name, 0.0))
        score += coefficient * float(value)
        used[name] = coefficient
    probability = 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, score))))
    return {
        "engine": "configurable-logistic-v1",
        "domain": "flood",
        "probability": round(probability, 6),
        "score": round(score, 6),
        "coefficients_used": used,
        "warning": "Coefficients must be calibrated and approved before operational use.",
    }


def vulnerability_scenario(
    indicators: dict[str, float], weights: dict[str, float], adjustments: dict[str, float]
) -> dict[str, object]:
    if not indicators:
        raise ValueError("At least one vulnerability indicator is required.")
    total_weight = sum(abs(float(weights.get(k, 0.0))) for k in indicators)
    if total_weight <= 0:
        raise ValueError("Scenario weights must include at least one non-zero value.")
    baseline = (
        sum(float(v) * float(weights.get(k, 0.0)) for k, v in indicators.items()) / total_weight
    )
    adjusted = {
        key: float(value) + float(adjustments.get(key, 0.0)) for key, value in indicators.items()
    }
    scenario = sum(adjusted[k] * float(weights.get(k, 0.0)) for k in adjusted) / total_weight
    return {
        "engine": "weighted-scenario-v1",
        "domain": "vulnerability",
        "baseline_score": round(baseline, 6),
        "scenario_score": round(scenario, 6),
        "delta": round(scenario - baseline, 6),
        "adjusted_indicators": adjusted,
        "warning": "Weights and scenario adjustments require stakeholder/scientific approval.",
    }
