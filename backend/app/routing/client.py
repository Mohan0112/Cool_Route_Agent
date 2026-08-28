"""Async client for two free, keyless OpenStreetMap-based services: Nominatim (address ->
coordinates) and OSRM (coordinates -> real street routes). FortyGuard's Temperature API has
no directions or address-search endpoint of its own, so these fill that gap -- the CoolRoute
agent combines them with FortyGuard's heatmap endpoint (see routing/geometry.py) to turn a
real route into a real measured-heat comparison.
"""
import httpx

from ..fortyguard.cache import ResponseCache
from .errors import RoutingError

# The single public router.project-osrm.org demo server only actually runs its car speed
# profile -- confirmed by testing: requesting "walking" or "cycling" there returns the exact
# same distance/duration as "driving" (a 16.76km "walk" came back as 18 minutes, ~55 km/h).
# OpenStreetMap.de hosts three separate, correctly-profiled OSRM instances instead, so each
# mode gets a realistic duration (foot ~4.5 km/h, bike ~14.5 km/h, car ~55 km/h on the same
# route). Still free, still keyless, still OSRM.
_MODE_HOSTS = {
    "walking": "https://routing.openstreetmap.de/routed-foot",
    "cycling": "https://routing.openstreetmap.de/routed-bike",
    "driving": "https://routing.openstreetmap.de/routed-car",
}
_NOMINATIM_USER_AGENT = "FortyGuard-CoolRoute-Hackathon26/1.0"


class RoutingClient:
    def __init__(self, nominatim_base_url: str, cache: ResponseCache, timeout_s: float = 20.0):
        self._nominatim_base_url = nominatim_base_url.rstrip("/")
        self._cache = cache
        self._timeout_s = timeout_s

    async def geocode(self, query: str) -> dict:
        params = {"query": query.strip().lower()}
        cached = self._cache.get("geocode", params)
        if cached is not None:
            return cached

        async with httpx.AsyncClient(timeout=self._timeout_s) as client:
            resp = await client.get(
                f"{self._nominatim_base_url}/search",
                params={"q": query, "format": "jsonv2", "limit": 1, "countrycodes": "us"},
                headers={"User-Agent": _NOMINATIM_USER_AGENT},
            )
        if not resp.is_success:
            raise RoutingError(f"Geocoding service error {resp.status_code} for {query!r}.")
        results = resp.json()
        if not results:
            raise RoutingError(
                f"Could not find a U.S. location matching {query!r}. Try a more specific address, "
                "landmark, or 'city, state'."
            )
        top = results[0]
        result = {"lat": float(top["lat"]), "lon": float(top["lon"]), "display_name": top["display_name"]}
        self._cache.put("geocode", params, result)
        return result

    async def route_alternatives(self, origin: tuple[float, float], destination: tuple[float, float], mode: str) -> list[dict]:
        host = _MODE_HOSTS.get(mode)
        if host is None:
            raise RoutingError(f"Unsupported travel mode {mode!r}; use walking, cycling, or driving.")

        params = {"origin": list(origin), "destination": list(destination), "mode": mode}
        cached = self._cache.get("osrm_route", params)
        if cached is not None:
            return cached

        o_lat, o_lon = origin
        d_lat, d_lon = destination
        coords = f"{o_lon},{o_lat};{d_lon},{d_lat}"
        async with httpx.AsyncClient(timeout=self._timeout_s) as client:
            resp = await client.get(
                f"{host}/route/v1/driving/{coords}",
                params={"alternatives": "true", "overview": "full", "geometries": "geojson", "steps": "true"},
            )
        if not resp.is_success:
            raise RoutingError(f"Routing service error {resp.status_code}.")
        body = resp.json()
        if body.get("code") != "Ok":
            raise RoutingError(f"No {mode} route found between those points ({body.get('code', 'unknown error')}).")

        routes = []
        for idx, route in enumerate(body["routes"]):
            routes.append(
                {
                    "route_id": idx,
                    "distance_m": route["distance"],
                    "duration_s": route["duration"],
                    "mode": mode,
                    "geometry_lonlat": route["geometry"]["coordinates"],
                    "streets": _major_streets(route["legs"]),
                }
            )
        self._cache.put("osrm_route", params, routes)
        return routes


def _major_streets(legs: list[dict], limit: int = 5) -> list[str]:
    names = []
    for leg in legs:
        for step in leg.get("steps", []):
            name = (step.get("name") or "").strip()
            if name and (not names or names[-1] != name):
                names.append(name)
    return names[:limit]
