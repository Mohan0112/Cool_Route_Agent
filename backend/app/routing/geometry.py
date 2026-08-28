"""Turns raw OSRM route geometry into a FortyGuard-compatible heatmap AOI polygon: a thin
buffered corridor that hugs the route line. FortyGuard's heatmap endpoint analyzes polygon
areas, not routes, so this is what lets the CoolRoute agent ask "how hot is it along this
specific path" using the same endpoint every other agent-style tool in this project uses.
"""
import math

MAX_CORRIDOR_AREA_KM2 = 100.0  # stays comfortably under FortyGuard's ~130km^2 heatmap cap
DEFAULT_HALF_WIDTH_KM = 0.05  # 100m total corridor width for a normal city route


def decimate(coords: list[list[float]], max_points: int = 60) -> list[list[float]]:
    """Thins a point list down to at most max_points, always keeping the first and last
    point. OSRM can return hundreds of points for a long route; we don't need that much
    detail for a heatmap AOI or for drawing a smooth line on a map.
    """
    if len(coords) <= max_points:
        return coords
    step = (len(coords) - 1) / (max_points - 1)
    indices = sorted({round(i * step) for i in range(max_points)})
    return [coords[i] for i in indices]


def _to_xy(lon: float, lat: float, ref_lat: float) -> tuple[float, float]:
    km_per_deg_lat = 110.574
    km_per_deg_lon = 111.320 * math.cos(math.radians(ref_lat))
    return lon * km_per_deg_lon, lat * km_per_deg_lat


def _to_lonlat(x: float, y: float, ref_lat: float) -> tuple[float, float]:
    km_per_deg_lat = 110.574
    km_per_deg_lon = 111.320 * math.cos(math.radians(ref_lat))
    return x / km_per_deg_lon, y / km_per_deg_lat


def corridor_polygon(coords_lonlat: list[list[float]], distance_m: float) -> dict:
    """Buffers a route line (list of [lon, lat], as returned by OSRM's GeoJSON geometry)
    into a closed polygon ring, returned as a GeoJSON FeatureCollection ready to hand to
    FortyGuard's heatmap endpoint. Corridor width auto-shrinks for very long routes so a
    cross-country driving route can never blow through the area cap the way a fixed width
    would.
    """
    coords = decimate(coords_lonlat)
    if len(coords) < 2:
        raise ValueError("Route geometry needs at least 2 points to build a corridor.")

    distance_km = max(distance_m / 1000.0, 0.05)
    half_width_km = min(DEFAULT_HALF_WIDTH_KM, MAX_CORRIDOR_AREA_KM2 / (2 * distance_km))

    ref_lat = sum(lat for _, lat in coords) / len(coords)
    pts = [_to_xy(lon, lat, ref_lat) for lon, lat in coords]

    # Per-vertex normal = average of the two adjacent segment normals, so the corridor
    # doesn't pinch or spike at turns the way a per-segment-only offset would.
    normals = []
    for i in range(len(pts)):
        segs = []
        if i > 0:
            segs.append((pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]))
        if i < len(pts) - 1:
            segs.append((pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]))
        sx = sum(s[0] for s in segs) / len(segs)
        sy = sum(s[1] for s in segs) / len(segs)
        length = math.hypot(sx, sy) or 1.0
        normals.append((-sy / length, sx / length))

    left = [(pts[i][0] + normals[i][0] * half_width_km, pts[i][1] + normals[i][1] * half_width_km) for i in range(len(pts))]
    right = [(pts[i][0] - normals[i][0] * half_width_km, pts[i][1] - normals[i][1] * half_width_km) for i in range(len(pts))]
    ring_xy = left + list(reversed(right)) + [left[0]]
    ring_lonlat = [list(_to_lonlat(x, y, ref_lat)) for x, y in ring_xy]

    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {"type": "Polygon", "coordinates": [ring_lonlat]},
            }
        ],
    }


def to_lat_lon(coords_lonlat: list[list[float]]) -> list[list[float]]:
    """Converts OSRM's [lon, lat] geometry into the [lat, lon] pairs Leaflet expects.

    Deliberately NOT decimated, unlike corridor_polygon/decimate above: a decimated line
    still looks fine on a short trip, but on a longer route it visibly cuts straight across
    curves and highway interchanges instead of following the actual road -- confirmed by the
    user's own screenshot (a route line floating diagonally across an I-70/US-6/US-50
    interchange instead of following the ramp). The full OSRM geometry for even a very long
    route is only a few thousand coordinate pairs (tens of KB as JSON), which is cheap for a
    once-per-run response -- not worth trading visual correctness for.
    """
    return [[lat, lon] for lon, lat in coords_lonlat]
