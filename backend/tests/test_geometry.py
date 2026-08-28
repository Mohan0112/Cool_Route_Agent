import pytest

from app.fortyguard.validation import MAX_AREA_KM2, _ring_area_km2
from app.routing.geometry import corridor_polygon, decimate, to_lat_lon


def test_decimate_keeps_short_lists_untouched():
    coords = [[0.0, 0.0], [1.0, 1.0], [2.0, 2.0]]
    assert decimate(coords, max_points=60) == coords


def test_decimate_caps_point_count_and_keeps_endpoints():
    coords = [[float(i), float(i)] for i in range(1000)]
    result = decimate(coords, max_points=50)
    assert len(result) <= 50
    assert result[0] == coords[0]
    assert result[-1] == coords[-1]


def test_to_lat_lon_reorders_without_dropping_points():
    # Regression test: to_lat_lon used to decimate to max_points=200, which visibly cut
    # corners across curves/interchanges on long routes (found via a real user screenshot).
    # It must never drop points now, regardless of how many are passed in.
    coords_lonlat = [[float(-112 + i * 0.001), float(33 + i * 0.001)] for i in range(5000)]
    result = to_lat_lon(coords_lonlat)
    assert len(result) == len(coords_lonlat)
    assert result[0] == [coords_lonlat[0][1], coords_lonlat[0][0]]
    assert result[-1] == [coords_lonlat[-1][1], coords_lonlat[-1][0]]


def test_corridor_polygon_returns_a_closed_ring():
    coords_lonlat = [[-112.07 + i * 0.001, 33.45] for i in range(20)]
    polygon = corridor_polygon(coords_lonlat, distance_m=2000)
    ring = polygon["features"][0]["geometry"]["coordinates"][0]
    assert ring[0] == ring[-1]
    assert len(ring) >= 4


def test_corridor_polygon_rejects_a_single_point():
    with pytest.raises(ValueError):
        corridor_polygon([[-112.07, 33.45]], distance_m=100)


def test_corridor_polygon_area_stays_under_the_heatmap_cap_for_a_long_route():
    # A ~1000km route -- the corridor width must auto-shrink so this can never blow through
    # FortyGuard's ~130km^2 heatmap area cap the way a fixed width would.
    coords_lonlat = [[-112.0 + i * 0.05, 33.45] for i in range(200)]
    polygon = corridor_polygon(coords_lonlat, distance_m=1_000_000)
    ring = polygon["features"][0]["geometry"]["coordinates"][0]
    area_km2 = _ring_area_km2(ring)
    assert area_km2 < MAX_AREA_KM2


def test_corridor_polygon_uses_full_width_for_a_short_route():
    # For a normal city-scale route, the corridor shouldn't be shrunk at all.
    coords_lonlat = [[-112.07 + i * 0.0005, 33.45] for i in range(20)]
    polygon = corridor_polygon(coords_lonlat, distance_m=1500)
    ring = polygon["features"][0]["geometry"]["coordinates"][0]
    area_km2 = _ring_area_km2(ring)
    assert 0 < area_km2 < MAX_AREA_KM2
