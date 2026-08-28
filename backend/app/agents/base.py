"""Shared Gemini tool-calling loop used by all 3 agents. They differ only in system prompt,
tool subset, and final-answer schema -- never in how this loop runs. Termination is a
structured `final_answer`-style tool call (declared by the caller as part of `tools`, name
given via `final_tool_name`), not freeform-text parsing, so every agent's output shape is
guaranteed structured.

A single module-level semaphore serializes all Gemini calls across every agent: a hackathon
demo has one presenter driving one agent at a time, not concurrent traffic, so this cheaply
removes 429/quota races instead of engineering real concurrency control.
"""
import asyncio
import json
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Optional

from google import genai
from google.genai import types

from ..fortyguard.tool_schema import ToolRegistry

_GEMINI_SEMAPHORE = asyncio.Semaphore(1)
_RETRYABLE_MARKERS = ("429", "RESOURCE_EXHAUSTED", "UNAVAILABLE", "503")


@dataclass
class AgentEvent:
    type: str  # "tool_call" | "tool_result" | "tool_error" | "progress" | "final" | "error"
    data: dict


def _jsonable(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except TypeError:
        return json.loads(json.dumps(value, default=str))


class AgentRunner:
    def __init__(self, api_key: str, model: str, max_turns: int = 8, timeout_s: float = 90.0):
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._max_turns = max_turns
        self._timeout_s = timeout_s

    async def _generate(self, contents: list, gemini_tool: types.Tool, system_prompt: str) -> types.GenerateContentResponse:
        config = types.GenerateContentConfig(system_instruction=system_prompt, tools=[gemini_tool])
        last_exc: Optional[Exception] = None
        async with _GEMINI_SEMAPHORE:
            for wait_s in (0, 2, 5, 10):
                if wait_s:
                    await asyncio.sleep(wait_s)
                try:
                    return await self._client.aio.models.generate_content(model=self._model, contents=contents, config=config)
                except Exception as exc:
                    last_exc = exc
                    if not any(marker in str(exc) for marker in _RETRYABLE_MARKERS):
                        raise
        raise last_exc  # exhausted retries on a retryable error

    async def run_stream(
        self,
        system_prompt: str,
        user_message: str,
        tools: ToolRegistry,
        final_tool_name: str,
    ) -> AsyncGenerator[AgentEvent, None]:
        gemini_tool = tools.to_gemini_tool()
        contents: list[types.Content] = [types.Content(role="user", parts=[types.Part(text=user_message)])]

        try:
            async with asyncio.timeout(self._timeout_s):
                for _turn in range(self._max_turns):
                    response = await self._generate(contents, gemini_tool, system_prompt)
                    calls = response.function_calls or []

                    if not calls:
                        yield AgentEvent("final", {"text": response.text or "", "structured": None})
                        return

                    contents.append(response.candidates[0].content)
                    function_response_parts = []

                    for call in calls:
                        args = dict(call.args or {})
                        yield AgentEvent("tool_call", {"name": call.name, "args": _jsonable(args)})

                        if call.name == final_tool_name:
                            yield AgentEvent("final", {"text": None, "structured": _jsonable(args)})
                            return

                        progress_messages: list[str] = []

                        async def on_progress(msg: str, _sink=progress_messages) -> None:
                            _sink.append(msg)

                        try:
                            result = await tools.dispatch(call.name, args, on_progress=on_progress)
                            for msg in progress_messages:
                                yield AgentEvent("progress", {"tool": call.name, "message": msg})
                            result = _jsonable(result)
                            yield AgentEvent("tool_result", {"name": call.name, "result": result})
                            function_response_parts.append(
                                types.Part(function_response=types.FunctionResponse(name=call.name, response={"result": result}))
                            )
                        except Exception as exc:
                            for msg in progress_messages:
                                yield AgentEvent("progress", {"tool": call.name, "message": msg})
                            yield AgentEvent("tool_error", {"name": call.name, "error": str(exc)})
                            function_response_parts.append(
                                types.Part(function_response=types.FunctionResponse(name=call.name, response={"error": str(exc)}))
                            )

                    contents.append(types.Content(role="user", parts=function_response_parts))

                yield AgentEvent("error", {"message": f"Stopped after {self._max_turns} turns without a final answer."})
        except TimeoutError:
            yield AgentEvent("error", {"message": f"Agent run exceeded its {self._timeout_s}s timeout."})
