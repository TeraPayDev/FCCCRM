from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import fmean


@dataclass(frozen=True)
class ForecastPoint:
    period: int
    value: float
    lower: float
    upper: float


@dataclass(frozen=True)
class TrendFit:
    slope: float
    intercept: float
    r_squared: float
    residual_sigma: float


def _fit_linear(values: list[float]) -> TrendFit:
    if len(values) < 2:
        raise ValueError("At least two observations are required for a trend forecast.")
    n = len(values)
    xs = list(range(n))
    xbar = fmean(xs)
    ybar = fmean(values)
    denominator = sum((x - xbar) ** 2 for x in xs)
    slope = sum((x - xbar) * (y - ybar) for x, y in zip(xs, values, strict=True)) / denominator
    intercept = ybar - slope * xbar
    fitted = [intercept + slope * x for x in xs]
    residuals = [actual - expected for actual, expected in zip(values, fitted, strict=True)]
    ss_res = sum(value**2 for value in residuals)
    ss_tot = sum((value - ybar) ** 2 for value in values)
    r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 1.0
    residual_sigma = math.sqrt(ss_res / max(1, n - 2))
    return TrendFit(slope, intercept, max(0.0, min(1.0, r_squared)), residual_sigma)


def _linear_forecast(values: list[float], periods: int) -> tuple[TrendFit, list[ForecastPoint]]:
    if periods < 1 or periods > 60:
        raise ValueError("Forecast periods must be between 1 and 60.")
    fit = _fit_linear(values)
    n = len(values)
    band = max(0.15, fit.residual_sigma * 1.96)
    points = [
        ForecastPoint(
            i + 1,
            fit.intercept + fit.slope * (n + i),
            fit.intercept + fit.slope * (n + i) - band,
            fit.intercept + fit.slope * (n + i) + band,
        )
        for i in range(periods)
    ]
    return fit, points


def heat_trend(values: list[float], periods: int = 7) -> dict[str, object]:
    fit, points = _linear_forecast(values, periods)
    return {
        "engine": "linear-trend-v2",
        "domain": "heat",
        "forecast": [
            {
                "period": p.period,
                "value": round(p.value, 3),
                "lower": round(p.lower, 3),
                "upper": round(p.upper, 3),
            }
            for p in points
        ],
        "metrics": {
            "slope_per_period": round(fit.slope, 6),
            "r_squared": round(fit.r_squared, 4),
            "residual_sigma": round(fit.residual_sigma, 4),
            "observations": len(values),
        },
        "trend_direction": (
            "WARMING" if fit.slope > 0.01 else "COOLING" if fit.slope < -0.01 else "STABLE"
        ),
        "warning": (
            "Engineering baseline only; confidence band reflects trend-fit residuals, "
            "not a calibrated operational climate model."
        ),
    }


def canopy_trend(values: list[float], periods: int = 4) -> dict[str, object]:
    fit, points = _linear_forecast(values, periods)
    return {
        "engine": "linear-trend-v2",
        "domain": "canopy",
        "forecast": [
            {
                "period": p.period,
                "value": round(max(0.0, min(100.0, p.value)), 3),
                "lower": round(max(0.0, min(100.0, p.lower)), 3),
                "upper": round(max(0.0, min(100.0, p.upper)), 3),
            }
            for p in points
        ],
        "metrics": {"slope_per_period": round(fit.slope, 6), "r_squared": round(fit.r_squared, 4)},
        "warning": (
            "Trend projection is bounded to 0-100%; field/remote-sensing validation is required."
        ),
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
