"""Single source of truth mapping Pydantic request models -> Gemini FunctionDeclarations
-> runtime dispatch, so the schema Gemini sees and the code that actually runs can never drift.

Confirmed via `google-genai` 1.64.0: `FunctionDeclaration.parameters_json_schema` accepts a
raw JSON Schema (including `$defs`/`$ref`/`anyOf`) directly -- no manual flattening needed,
unlike the older constrained `parameters` (Schema-object) field.
"""
import inspect
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from google.genai import types
from pydantic import BaseModel


@dataclass
class ToolSpec:
    name: str
    description: str
    params_model: type[BaseModel]
    handler: Callable[..., Awaitable[Any]]
    _accepts_progress: bool = field(init=False, repr=False)

    def __post_init__(self):
        self._accepts_progress = "on_progress" in inspect.signature(self.handler).parameters

    def to_function_declaration(self) -> types.FunctionDeclaration:
        schema = self.params_model.model_json_schema()
        schema.pop("title", None)
        return types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters_json_schema=schema,
        )


async def identity_handler(**kwargs):
    """Placeholder handler for final-answer tools -- AgentRunner intercepts calls to the
    designated final-tool name before dispatch, so this never actually runs."""
    return kwargs


class ToolRegistry:
    def __init__(self, specs: list[ToolSpec]):
        self._specs = {spec.name: spec for spec in specs}

    def __getitem__(self, name: str) -> ToolSpec:
        return self._specs[name]

    def __contains__(self, name: str) -> bool:
        return name in self._specs

    def subset(self, names: list[str]) -> "ToolRegistry":
        return ToolRegistry([self._specs[n] for n in names])

    def with_added(self, spec: ToolSpec) -> "ToolRegistry":
        return ToolRegistry([*self._specs.values(), spec])

    def to_gemini_tool(self) -> types.Tool:
        return types.Tool(function_declarations=[spec.to_function_declaration() for spec in self._specs.values()])

    async def dispatch(self, name: str, args: dict, on_progress=None) -> Any:
        spec = self._specs[name]
        validated = spec.params_model.model_validate(args)
        kwargs = validated.model_dump(exclude_none=True)
        if spec._accepts_progress:
            kwargs["on_progress"] = on_progress
        return await spec.handler(**kwargs)
