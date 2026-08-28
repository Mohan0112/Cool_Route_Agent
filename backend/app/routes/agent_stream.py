"""Shared SSE-streaming + persistence logic for every agent route. Each agent module only
supplies its system prompt, tool subset, and final-answer tool name -- everything about how
a run is streamed to the browser and saved for replay lives here, once.
"""
import json
from datetime import date
from typing import Awaitable, Callable, AsyncGenerator, Optional

from sse_starlette.sse import ServerSentEvent

from ..agents.base import AgentEvent, AgentRunner
from ..fortyguard.tool_schema import ToolRegistry
from ..storage.repo import RunRepo


def _with_today_grounding(system_prompt: str) -> str:
    """LLMs trained with a past cutoff tend to assume a year like 2026 must be in the
    future and 'invent' a historical fallback date even when today's date is actually
    valid -- confirmed by direct testing. Grounding the prompt with the real current date
    fixes this without touching each agent's own instructions.
    """
    today = date.today().isoformat()
    return (
        f"{system_prompt}\n\nToday's real-world date is {today}. Treat this as ground truth: "
        f"dates on or before {today} are NOT in the future, regardless of what your training "
        f"data might suggest. Only dates after {today} count as forecasting."
    )


async def stream_agent_run(
    *,
    agent_kind: str,
    system_prompt: str,
    user_message: str,
    tools: ToolRegistry,
    final_tool_name: str,
    agent_runner: AgentRunner,
    run_repo: RunRepo,
    enrich_final: Optional[Callable[[dict], Awaitable[dict]]] = None,
) -> AsyncGenerator[ServerSentEvent, None]:
    run_id = run_repo.create_run(agent_kind, user_message)
    yield ServerSentEvent(event="run_started", data=json.dumps({"run_id": run_id}))

    seq = 0
    final_result = None
    status = "succeeded"
    try:
        grounded_prompt = _with_today_grounding(system_prompt)
        async for event in agent_runner.run_stream(grounded_prompt, user_message, tools, final_tool_name):
            if event.type == "final" and enrich_final and event.data.get("structured") is not None:
                # Enrich (e.g. attach map geometry the LLM never has to echo back) BEFORE
                # yielding, since the SSE "final" event is what the frontend actually renders --
                # anything done only afterwards would never reach the browser.
                enriched = await enrich_final(event.data["structured"])
                event = AgentEvent("final", {"text": event.data.get("text"), "structured": enriched})
            seq += 1
            run_repo.append_event(run_id, seq, event.type, event.data)
            yield ServerSentEvent(event=event.type, data=json.dumps(event.data))
            if event.type == "final":
                final_result = event.data.get("structured") or {"text": event.data.get("text")}
            elif event.type == "error":
                status = "failed"
    except Exception as exc:  # noqa: broad -- must not let a bug crash the SSE stream mid-flight
        seq += 1
        error_data = {"message": str(exc)}
        run_repo.append_event(run_id, seq, "error", error_data)
        yield ServerSentEvent(event="error", data=json.dumps(error_data))
        status = "failed"

    run_repo.finish_run(run_id, status, final_result)
    yield ServerSentEvent(event="run_finished", data=json.dumps({"run_id": run_id, "status": status}))
