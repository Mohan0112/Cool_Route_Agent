from datetime import date, timedelta

import pytest

from app.fortyguard.errors import ValidationError
from app.fortyguard.validation import (
    ensure_ring_closed,
    validate_date_range,
    validate_point_us,
    validate_polygon_area,
)


def test_validate_point_us_accepts_phoenix():
    validate_point_us(33.4484, -112.074)  # should not raise


def test_validate_point_us_rejects_outside_us():
    with pytest.raises(ValidationError):
        validate_point_us(48.8566, 2.3522)  # Paris


def test_validate_date_range_rejects_before_coverage_start():
    with pytest.raises(ValidationError):
        validate_date_range("2020-12-31")


def test_validate_date_range_accepts_today():
    validate_date_range(date.today().isoformat())  # should not raise


def test_validate_date_range_rejects_future_without_forecast():
    future = (date.today() + timedelta(days=5)).isoformat()
    with pytest.raises(ValidationError):
        validate_date_range(future, allow_forecast=False)


def test_ensure_ring_closed_closes_an_open_ring():
    polygon = {
        "features": [
            {"geometry": {"coordinates": [[[-112.0, 33.0], [-112.0, 33.1], [-111.9, 33.1], [-111.9, 33.0]]]}}
        ]
    }
    closed = ensure_ring_closed(polygon)
    ring = closed["features"][0]["geometry"]["coordinates"][0]
    assert ring[0] == ring[-1]


def test_validate_polygon_area_rejects_an_oversized_polygon():
    # A ~1 degree square is roughly 10,000+ km^2, far past the ~130km^2 cap.
    huge_ring = [[-112.0, 33.0], [-112.0, 34.0], [-111.0, 34.0], [-111.0, 33.0], [-112.0, 33.0]]
    polygon = {"features": [{"geometry": {"coordinates": [huge_ring]}}]}
    with pytest.raises(ValidationError):
        validate_polygon_area(polygon)
