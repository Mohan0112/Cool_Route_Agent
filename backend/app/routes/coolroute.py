from datetime import date

from fastapi import APIRouter
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from .. import deps
from ..agents import coolroute_agent
from ..agents.coolroute_agent import heat_risk_category
from ..routing.geometry import to_lat_lon
from .agent_stream import stream_agent_run

router = APIRouter(prefix="/api/agents/coolroute", tags=["coolroute"])

# Fixed spread of times used for the opt-in "compare departure times" feature -- deciding
# these in Python (not asking the LLM to invent them) keeps the comparison consistent and
# demoable ("we always check morning/midday/afternoon/evening") rather than model-dependent.
DEPARTURE_TIME_PRESETS = ["09:00", "12:00", "15:00", "18:00"]


class CoolRouteRequest(BaseModel):
    origin: str
    destination: str
    mode: str = "walking"
    when: str = "now"  # "now", or a free-text date/time like "2026-08-27 14:00"
    compare_departure_times: bool = False


def _resolve_date(when: str) -> str:
    when = when.strip()
    if when.lower() == "now":
        return date.today().isoformat()
    return when.split(" ")[0]  # "YYYY-MM-DD HH:MM" -> "YYYY-MM-DD"


def _build_user_message(body: CoolRouteRequest) -> str:
    when_clause = "right now (use the current real-world date/time)" if body.when.strip().lower() == "now" else f"departing at {body.when}"
    message = (
        f"Find the best {body.mode} route from '{body.origin}' to '{body.destination}', {when_clause}. "
        "Rank the real route alternatives by measured heat exposure and recommend the coolest reasonable option."
    )
    if body.compare_departure_times:
        times = ", ".join(DEPARTURE_TIME_PRESETS)
        message += (
            f" Additionally, once you've picked your recommended route, call compare_departure_times for "
            f"that route using date {_resolve_date(body.when)} and times [{times}], and include the results "
            "in departure_time_comparison so the user can see which time of day is coolest to leave."
        )
    return message


@router.post("/run")
async def run_coolroute(body: CoolRouteRequest):
    session: dict = {}
    client = deps.get_fortyguard_client()
    routing_client = deps.get_routing_client()
    tools = coolroute_agent.build_registry(client, routing_client, session)

    async def enrich_final(structured: dict) -> dict:
        routes = session.get("routes", {})
        for option in structured.get("options", []):
            route = routes.get(str(option.get("route_id")))
            if route is not None:
                option["geometry"] = to_lat_lon(route["geometry_lonlat"])
            category, tip = heat_risk_category(option.get("max_temp_c"))
            option["risk_category"] = category
            option["safety_tip"] = tip
        return structured

    generator = stream_agent_run(
        agent_kind=coolroute_agent.NAME,
        system_prompt=coolroute_agent.SYSTEM_PROMPT,
        user_message=_build_user_message(body),
        tools=tools,
        final_tool_name=coolroute_agent.FINAL_TOOL_NAME,
        agent_runner=deps.get_agent_runner(),
        run_repo=deps.get_run_repo(),
        enrich_final=enrich_final,
    )
    return EventSourceResponse(generator)


@router.get("/runs/{run_id}")
async def get_coolroute_run(run_id: str):
    return deps.get_run_repo().get_run(run_id)
