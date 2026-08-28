"""The CoolRoute Agent -- Track 6's flagship example, built for real: given an origin, a
destination, and a travel mode, it geocodes both ends, pulls real street route alternatives,
measures real FortyGuard heat data along each one, and recommends which to take. Like Google
Maps, but the ranking criterion is temperature and sun exposure, not just time.

Tool state (which routes exist, keyed by route_id) is scoped to a single agent run via the
`session` dict passed into build_registry -- there's one HTTP request per run, so this is
simpler and safer than any global/shared cache would be.

Two tools (geocode_locations, estimate_route_heat) are deliberately "batched" -- they resolve
both trip endpoints, or every route candidate, in ONE call instead of one call per item. This
is a real latency fix, not just a convenience: every tool call costs a full serialized Gemini
round-trip (base.py's AgentRunner uses a single semaphore across all calls), so cutting the
call count from ~7 turns to ~4 cuts wall-clock time roughly in half. A third, opt-in tool
(compare_departure_times) adds one more turn only when the user actually asks for it.
"""
import asyncio
from typing import Literal, Optional

from pydantic import BaseModel, Field

from ..fortyguard.client import FortyGuardClient
from ..fortyguard.models import DateTimeSpec
from ..fortyguard.tool_schema import ToolRegistry, ToolSpec, identity_handler
from ..routing.client import RoutingClient
from ..routing.geometry import corridor_polygon, decimate

NAME = "coolroute"
FINAL_TOOL_NAME = "submit_route_plan"

SYSTEM_PROMPT = """You are FortyGuard's CoolRoute Agent for Track 6 of the Hackathon'26 Agentic Track.

Goal: given an origin, a destination, and a travel mode, find real street routes between them
and recommend which one to take based on ACTUAL measured heat exposure along each route --
never invent temperature numbers, solar irradiance numbers, or routes, always call a tool to
get them.

How to work, step by step:
1. Call geocode_locations ONCE with both the origin_query and destination_query -- this resolves
   both ends of the trip in a single call instead of two separate ones.
2. Call get_route_alternatives once with those coordinates and the requested mode. This returns
   every real candidate route (route_id, distance, duration, major streets) -- do not guess or
   invent routes yourself, only use exactly what this tool returns.
3. Call estimate_route_heat ONCE, passing the route_ids of EVERY route returned (e.g. [0, 1, 2])
   together in one call, all using the exact same date_time, so the comparison between routes is
   fair. This measures both mean/max temperature AND average solar irradiance (direct sun
   exposure) along each route's corridor. Published heat-routing research shows sun exposure
   varies far more than air temperature within a route, so weigh BOTH signals, not just
   temperature, when judging which route is genuinely most comfortable -- a route with slightly
   higher temperature but much lower solar irradiance (more shade) can be the better pick.
4. If a tool call fails, adapt and generalize the fix to every remaining call rather than repeating
   the same mistake -- e.g. if a date is rejected as out of range, immediately switch ALL remaining
   calls to a valid date. If geocoding fails for an address, do not invent coordinates -- report
   the failure.
5. Label each route you include: "Fastest" for the shortest duration, "Coolest" for the best
   combination of low temperature and low solar irradiance, and "Balanced" for the best trade-off
   between speed and comfort. If there's only one route, or two routes tie, only include the
   labels that genuinely apply -- never invent routes that don't exist just to fill out three
   options.
6. Call submit_route_plan with your final structured answer. Every option must cite real numbers
   from estimate_route_heat (temperature AND solar irradiance), and rationale must explain the
   trade-off in plain language (e.g. "2 minutes slower but 3.1C cooler with less direct sun,
   avoids full sun on 7th Ave"). Do not invent a risk category or safety tip yourself -- those are
   added automatically after you submit.
7. Always include one concrete measured_outcome sentence, e.g. "The coolest route is 3.1C cooler
   and has noticeably less solar exposure than the fastest route, and only adds 2 minutes." --
   judges specifically look for a measurable outcome, not a vague summary.
8. ONLY if the request explicitly asks you to compare departure times: after picking your
   recommended route, call compare_departure_times exactly once for that route_id, using the
   exact date and times given in the request -- do not invent different times. Include the
   results in departure_time_comparison and mention the coolest time to leave in your summary.
   If departure-time comparison was NOT requested, leave departure_time_comparison out entirely
   and do not call compare_departure_times.

Constraints you must respect: FortyGuard only covers U.S. locations, and dates are limited to
2021-01-01 through today (no long-range forecasting)."""


class GeocodeLocationsParams(BaseModel):
    origin_query: str = Field(description="A U.S. address, landmark, or 'City, State' for the trip's starting point.")
    destination_query: str = Field(description="A U.S. address, landmark, or 'City, State' for the trip's destination.")


class RouteAlternativesParams(BaseModel):
    origin_lat: float
    origin_lon: float
    destination_lat: float
    destination_lon: float
    mode: Literal["walking", "cycling", "driving"] = Field(description="Travel mode to route for.")


class EstimateRouteHeatParams(BaseModel):
    route_ids: list[int] = Field(description="ALL route_ids returned by get_route_alternatives, checked together in one call.")
    date_time: DateTimeSpec


class CompareDepartureTimesParams(BaseModel):
    route_id: int = Field(description="The route_id to check across different times -- normally your recommended route.")
    date: str = Field(description="YYYY-MM-DD date to check, matching the date already used for this trip.")
    times: list[str] = Field(description="The exact HH:MM times to compare, as given in the request -- do not invent your own.")


class RouteOption(BaseModel):
    route_id: int = Field(description="The route_id this option corresponds to, from get_route_alternatives.")
    label: str = Field(description="Short label: 'Fastest', 'Coolest', 'Balanced', or similar -- only if it genuinely applies.")
    distance_km: float
    duration_min: float
    mean_temp_c: float = Field(description="Real mean temperature from estimate_route_heat for this route_id.")
    max_temp_c: float = Field(description="Real max temperature from estimate_route_heat for this route_id.")
    mean_solar_irradiance_wm2: Optional[float] = Field(
        default=None, description="Real mean solar irradiance (W/m^2) from estimate_route_heat for this route_id -- lower means more shade."
    )
    rationale: str = Field(description="Plain-language trade-off explanation citing the real numbers, including solar exposure.")


class DepartureTimeOption(BaseModel):
    time: str = Field(description="HH:MM time this measurement is for.")
    mean_temp_c: float = Field(description="Real mean temperature from compare_departure_times for this time.")
    mean_solar_irradiance_wm2: Optional[float] = Field(default=None, description="Real mean solar irradiance (W/m^2) for this time.")


class CoolRoutePlan(BaseModel):
    origin_label: str = Field(description="Human-readable resolved origin, e.g. from geocode_locations's display_name.")
    destination_label: str = Field(description="Human-readable resolved destination.")
    mode: Literal["walking", "cycling", "driving"]
    summary: str = Field(description="1-2 sentence plain-language recommendation.")
    options: list[RouteOption]
    measured_outcome: str = Field(description="One concrete, quantified outcome statement (e.g. '~3C cooler, less direct sun').")
    sources: list[str] = Field(description="Which tools/endpoints were called to produce this plan.")
    caveats: Optional[str] = Field(default=None, description="Any failed calls, skipped routes, or assumptions made.")
    departure_time_comparison: Optional[list[DepartureTimeOption]] = Field(
        default=None,
        description="Only include this if the request explicitly asked to compare departure times -- heat at a few different times for your recommended route.",
    )


def heat_risk_category(temp_c: Optional[float]) -> tuple[str, str]:
    """Maps a route's peak temperature to a plain-language risk band + safety tip, loosely
    modeled on the U.S. National Weather Service's heat index categories (adapted to Celsius).
    Computed server-side from the LLM's own reported max_temp_c rather than asked of the LLM,
    so every route gets a consistent, deterministic label regardless of model wording.
    """
    if temp_c is None:
        return "Unknown", "Heat data unavailable for this route."
    if temp_c < 27:
        return "Comfortable", "No special precautions needed."
    if temp_c < 32:
        return "Caution", "Stay hydrated and take breaks in shade where possible."
    if temp_c < 39:
        return "Extreme Caution", "Carry water, seek shade often, and avoid heavy exertion."
    if temp_c < 51:
        return "Danger", "Avoid prolonged exposure -- reschedule if possible, or take frequent shaded breaks."
    return "Extreme Danger", "High risk of heat illness -- avoid this route or time if you can."


def _unwrap(result: dict) -> dict:
    """Demo-mode fixtures return fields at the top level; live FortyGuard results nest them
    under a "result" key -- this normalizes both so callers don't need to know which mode is
    active."""
    nested = result.get("result")
    return nested if isinstance(nested, dict) else result


def build_registry(client: FortyGuardClient, routing_client: RoutingClient, session: dict) -> ToolRegistry:
    async def _geocode_locations(origin_query: str, destination_query: str) -> dict:
        origin, destination = await asyncio.gather(
            routing_client.geocode(origin_query),
            routing_client.geocode(destination_query),
        )
        return {"origin": origin, "destination": destination}

    async def _get_route_alternatives(
        origin_lat: float, origin_lon: float, destination_lat: float, destination_lon: float, mode: str
    ) -> list[dict]:
        routes = await routing_client.route_alternatives((origin_lat, origin_lon), (destination_lat, destination_lon), mode)
        session["routes"] = {str(r["route_id"]): r for r in routes}
        return [
            {
                "route_id": r["route_id"],
                "distance_km": round(r["distance_m"] / 1000, 2),
                "duration_min": round(r["duration_s"] / 60, 1),
                "mode": r["mode"],
                "major_streets": r["streets"],
            }
            for r in routes
        ]

    async def _measure_route_at(route: dict, date_time: dict, on_progress) -> dict:
        """Shared by both estimate_route_heat (vary route, fixed time) and
        compare_departure_times (fixed route, vary time) -- both ultimately need the same
        "how hot is this specific corridor at this specific date_time" measurement."""
        polygon_aoi = corridor_polygon(route["geometry_lonlat"], route["distance_m"])
        # Sample solar irradiance at a few points along the route (start/middle/end) rather
        # than every vertex -- cheap enough to run alongside the heatmap call, and enough to
        # approximate how much of the route sits in direct sun vs shade.
        sample_points = decimate(route["geometry_lonlat"], max_points=3)

        heat_task = client.create_heatmap(polygon_aoi=polygon_aoi, date_time=date_time, analytic_type="tcm", on_progress=on_progress)
        solar_tasks = [client.environmental_parameters(point={"lat": lat, "lon": lon}, date_time=date_time) for lon, lat in sample_points]
        heat_result, *solar_results = await asyncio.gather(heat_task, *solar_tasks)

        stats = _unwrap(heat_result).get("stats_data") or {}
        irradiances = [v for v in (_unwrap(r).get("solar_irradiance_w_m2") for r in solar_results) if v is not None]
        mean_irradiance = round(sum(irradiances) / len(irradiances), 1) if irradiances else None

        return {
            "mean_temp_c": stats.get("mean"),
            "min_temp_c": stats.get("min"),
            "max_temp_c": stats.get("max"),
            "mean_solar_irradiance_wm2": mean_irradiance,
        }

    async def _estimate_one_route(route_id: int, date_time: dict, on_progress) -> dict:
        route = session.get("routes", {}).get(str(route_id))
        if route is None:
            raise ValueError(f"Unknown route_id {route_id}; call get_route_alternatives first.")
        measured = await _measure_route_at(route, date_time, on_progress)
        return {"route_id": route_id, **measured}

    async def _estimate_route_heat(route_ids: list[int], date_time: dict, on_progress=None) -> list[dict]:
        # Every route is measured concurrently -- wall-clock time is ~the slowest single
        # FortyGuard call, not the sum of all of them, regardless of how many routes there are.
        return await asyncio.gather(*(_estimate_one_route(route_id, date_time, on_progress) for route_id in route_ids))

    async def _compare_departure_times(route_id: int, date: str, times: list[str], on_progress=None) -> list[dict]:
        route = session.get("routes", {}).get(str(route_id))
        if route is None:
            raise ValueError(f"Unknown route_id {route_id}; call get_route_alternatives first.")

        async def one_time(time_str: str) -> dict:
            date_time = {"start_date": date, "start_time": time_str, "filter_type": 1}
            measured = await _measure_route_at(route, date_time, on_progress)
            return {"time": time_str, **measured}

        return await asyncio.gather(*(one_time(t) for t in times))

    return ToolRegistry(
        [
            ToolSpec(
                name="geocode_locations",
                description="Resolve BOTH the origin and destination (U.S. addresses, landmarks, or 'City, State') into latitude/longitude in a single call.",
                params_model=GeocodeLocationsParams,
                handler=_geocode_locations,
            ),
            ToolSpec(
                name="get_route_alternatives",
                description="Get real street-level route alternatives between two geocoded points for a travel mode (walking, cycling, or driving). Returns each candidate's route_id, distance, duration, and major streets -- pass every route_id returned to estimate_route_heat.",
                params_model=RouteAlternativesParams,
                handler=_get_route_alternatives,
            ),
            ToolSpec(
                name="estimate_route_heat",
                description="Get real measured temperature AND solar irradiance along EVERY listed route's corridor via FortyGuard's heatmap and environmental-parameters endpoints. Pass ALL route_ids from get_route_alternatives together in one call -- much faster than one call per route. Uses the same date_time for every route so the comparison is fair.",
                params_model=EstimateRouteHeatParams,
                handler=_estimate_route_heat,
            ),
            ToolSpec(
                name="compare_departure_times",
                description="ONLY call this if the request explicitly asks to compare departure times. Measures real temperature and solar irradiance for ONE route across several times of day, so the user can see which time is coolest to leave.",
                params_model=CompareDepartureTimesParams,
                handler=_compare_departure_times,
            ),
            ToolSpec(
                name=FINAL_TOOL_NAME,
                description="Submit your final ranked route plan. Call this only after checking real heat data for every route option you include.",
                params_model=CoolRoutePlan,
                handler=identity_handler,
            ),
        ]
    )
