"""Collection classes for managing multiple tools."""

from typing import Any, Union, Type

from anthropic.types.beta import BetaToolUnionParam

from .base import (
    BaseAnthropicTool,
    ToolError,
    ToolFailure,
    ToolResult,
)


class ToolCollection:
    """A collection of anthropic-defined tools."""

    def __init__(self, *tools: Union[BaseAnthropicTool, Type[BaseAnthropicTool]]):
        self.tools = []
        for tool in tools:
            if isinstance(tool, type):
                # If it's a class, instantiate it
                self.tools.append(tool())
            else:
                # If it's already an instance, use it as is
                self.tools.append(tool)

        self.tool_map = {tool.to_params()["name"]: tool for tool in self.tools}

    def to_params(
        self,
    ) -> list[BetaToolUnionParam]:
        return [tool.to_params() for tool in self.tools]

    async def run(self, *, name: str, tool_input: dict[str, Any]) -> ToolResult:
        tool = self.tool_map.get(name)
        if not tool:
            return ToolFailure(error=f"Tool {name} is invalid")
        try:
            return await tool(**tool_input)
        except ToolError as e:
            return ToolFailure(error=e.message)
