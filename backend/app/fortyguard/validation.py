"""Client-side validation of the handbook's hard constraints, enforced BEFORE any network
call so we never pay for (or wait on) a request FortyGuard would reject anyway.
"""
import math
from datetime import date, datetime, timedelta

from .errors import ValidationError

# Practical U.S. coverage bounding boxes (continental US, Alaska, Hawaii). Heuristic, not
# an authoritative boundary service -- good enough to reject obviously-non-US coordinates
# before spending a network call.
US_BOUNDING_BOXES = [
    (24.0, 50.0, -125.5, -66.0),   # continental US
    (51.0, 72.0, -180.0, -129.0),  # Alaska
    (18.5, 22.5, -160.5, -154.5),  # Hawaii
]

EARLIEST_DATE = date(2021, 1, 1)
HEATMAP_FORECAST_HOURS = 12
MAX_AREA_KM2 = 130.0


def _in_us_bounds(lat: float, lon: float) -> bool:
    return any(min_lat <= lat <= max_lat and min_lon <= lon <= max_lon for min_lat, max_lat, min_lon, max_lon in US_BOUNDING_BOXES)


def validate_point_us(lat: float, lon: float) -> None:
    if not _in_us_bounds(lat, lon):
        raise ValidationError(
            f"Point ({lat}, {lon}) is outside FortyGuard's U.S.-only coverage area."
        )


def validate_polygon_us(polygon_aoi: dict) -> None:
    ring = _extract_ring(polygon_aoi)
    for lon, lat in ring:
        if not _in_us_bounds(lat, lon):
            raise ValidationError(
                f"Polygon vertex ({lat}, {lon}) is outside FortyGuard's U.S.-only coverage area."
            )


def _extract_ring(polygon_aoi: dict) -> list[tuple[float, float]]:
    try:
        feature = polygon_aoi["features"][0]
        coords = feature["geometry"]["coordinates"][0]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValidationError("polygon_aoi must be a GeoJSON FeatureCollection with one Polygon feature.") from exc
    return [(pt[0], pt[1]) for pt in coords]


def ensure_ring_closed(polygon_aoi: dict) -> dict:
    """Auto-closes an open ring (first point != last point) rather than rejecting it outright,
    since this is an easy, common mistake for a caller (human or LLM) to make.
    """
    feature = polygon_aoi["features"][0]
    coords = feature["geometry"]["coordinates"][0]
    if coords[0] != coords[-1]:
        coords = [*coords, coords[0]]
        feature["geometry"]["coordinates"][0] = coords
    return polygon_aoi


def validate_date_range(start_date: str, *, allow_forecast: bool = False) -> None:
    try:
        parsed = datetime.strptime(start_date, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValidationError(f"start_date {start_date!r} is not in YYYY-MM-DD format.") from exc

    if parsed < EARLIEST_DATE:
        raise ValidationError(f"start_date {start_date} is before FortyGuard's coverage start (2021-01-01).")

    latest = date.today()
    if allow_forecast:
        latest = (datetime.utcnow() + timedelta(hours=HEATMAP_FORECAST_HOURS)).date()

    if parsed > latest:
        raise ValidationError(
            f"start_date {start_date} is too far in the future "
            f"(heatmap allows up to +{HEATMAP_FORECAST_HOURS}h ahead; other endpoints allow no forecasting)."
            if allow_forecast
            else f"start_date {start_date} is in the future; only heatmap supports forecasting."
        )


def validate_polygon_area(polygon_aoi: dict) -> None:
    ring = _extract_ring(polygon_aoi)
    area_km2 = _ring_area_km2(ring)
    if area_km2 > MAX_AREA_KM2:
        raise ValidationError(
            f"Polygon area (~{area_km2:.1f} km²) exceeds the ~{MAX_AREA_KM2:.0f} km² cap per heatmap request. "
            "Split it into smaller polygons."
        )


def _ring_area_km2(ring: list[tuple[float, float]]) -> float:
    """Equirectangular-projection shoelage estimate -- accurate enough for the small AOIs
    this project deals with (a neighborhood, not a continent); no geo library dependency needed.
    """
    if len(ring) < 4:
        return 0.0
    avg_lat_rad = math.radians(sum(lat for _, lat in ring) / len(ring))
    km_per_deg_lat = 110.574
    km_per_deg_lon = 111.320 * math.cos(avg_lat_rad)

    pts = [(lon * km_per_deg_lon, lat * km_per_deg_lat) for lon, lat in ring]
    area = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def validate_heatmap_request(polygon_aoi: dict, start_date: str) -> dict:
    polygon_aoi = ensure_ring_closed(polygon_aoi)
    validate_polygon_us(polygon_aoi)
    validate_polygon_area(polygon_aoi)
    validate_date_range(start_date, allow_forecast=True)
    return polygon_aoi


def validate_point_request(lat: float, lon: float, start_date: str) -> None:
    validate_point_us(lat, lon)
    validate_date_range(start_date, allow_forecast=False)
