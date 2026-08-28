"""Deterministic synthetic fixtures for DEMO_MODE. Rather than storing a static JSON blob
per query (which would only ever "work" for one hardcoded location), we generate plausible
temperature data as a function of the actual request -- latitude, season, time of day, and
a stable hash of the coordinates for per-site variety -- so every demo site gets a distinct,
repeatable value instead of one canned number everywhere.
"""
import hashlib
import math
from datetime import datetime

from .errors import PlanRestrictedError

PREMIUM_ENDPOINTS = {"satellite", "streetview", "heat_intelligence"}


def _stable_jitter(*parts: str, spread: float = 1.0) -> float:
    digest = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return (int(digest[:8], 16) / 0xFFFFFFFF - 0.5) * 2 * spread


def _seasonal_base_c(lat: float, month: int, hour: int) -> float:
    # Warmer near the equator, peak in local summer, peak in mid-afternoon.
    latitude_factor = max(0.0, 1.0 - abs(lat) / 60.0)
    seasonal = math.sin((month - 4) / 12 * 2 * math.pi) * (10 if lat >= 0 else -10)
    diurnal = math.sin((hour - 6) / 24 * 2 * math.pi) * 6
    return 18 + latitude_factor * 14 + seasonal + diurnal


def fake_heatmap_result(polygon_aoi: dict, date_time: dict, granularity: int, analytic_type: str | None) -> dict:
    ring = polygon_aoi["features"][0]["geometry"]["coordinates"][0]
    lats = [pt[1] for pt in ring]
    lons = [pt[0] for pt in ring]
    center_lat, center_lon = sum(lats) / len(lats), sum(lons) / len(lons)

    dt = datetime.strptime(date_time["start_date"], "%Y-%m-%d")
    hour = int(date_time.get("start_time", "14:00").split(":")[0])
    base = _seasonal_base_c(center_lat, dt.month, hour)
    jitter = _stable_jitter(str(round(center_lat, 3)), str(round(center_lon, 3)), date_time["start_date"], str(hour))
    mean = round(base + jitter, 2)
    spread = 1.2
    n_cells = max(4, int(200 / max(granularity, 1)))

    return {
        "activity_id": f"demo-{_stable_jitter.__name__}-{abs(hash((center_lat, center_lon, date_time['start_date'])))}",
        "status": "completed",
        "stats_data": {
            "analytic_type": analytic_type or "tcm",
            "units": "celsius",
            "n_cells": n_cells,
            "min": round(mean - spread, 2),
            "max": round(mean + spread, 2),
            "mean": mean,
        },
        "from_cache": False,
        "demo_mode": True,
    }


def fake_env_params_result(point: dict, date_time: dict) -> dict:
    dt = datetime.strptime(date_time["start_date"], "%Y-%m-%d")
    hour = int(date_time.get("start_time", "14:00").split(":")[0])
    base = _seasonal_base_c(point["lat"], dt.month, hour)
    jitter = _stable_jitter(str(round(point["lat"], 3)), str(round(point["lon"], 3)), date_time["start_date"])
    temp_c = round(base + jitter, 2)
    return {
        "status": "completed",
        "temperature_c": temp_c,
        "heat_index_c": round(temp_c + max(0.0, (temp_c - 27) * 0.4), 2),
        "aqi": 40 + int(abs(jitter) * 30),
        "solar_irradiance_w_m2": round(500 + jitter * 100, 1),
        "from_cache": False,
        "demo_mode": True,
    }


def fake_usage_result() -> dict:
    return {
        "credit_summary": {
            "total_available_credits": 2_000_000,
            "cycle_credits_used": 0,
            "cycle_remaining_credits": 2_000_000,
        },
        "demo_mode": True,
    }


def raise_premium_restricted(endpoint: str) -> None:
    raise PlanRestrictedError(
        403,
        f"Premium plan required for '{endpoint}' (demo mode simulates the trial key's actual restriction).",
        {"endpoint": endpoint, "demo_mode": True},
    )
