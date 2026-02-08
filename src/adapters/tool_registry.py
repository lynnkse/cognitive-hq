"""Tool Registry — dispatches tool calls from CloudCode plans to adapter implementations.

Registered tools:
- telegram_send_message
- memory_put
- memory_search
- memory_get_latest
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from src.adapters.memory_emulator import MemoryEmulator
from src.adapters.telegram_emulator import TelegramEmulator
from src.runner.plan_schema import ToolCall

logger = logging.getLogger(__name__)


class ToolExecutionError(Exception):
    """Raised when a tool call fails during execution."""


class ToolRegistry:
    """Maps tool names to callable implementations and dispatches tool calls."""

    def __init__(
        self,
        telegram: TelegramEmulator,
        memory: MemoryEmulator,
    ):
        self._tools: dict[str, Callable[..., Any]] = {
            "telegram_send_message": telegram.send_message,
            "memory_put": memory.memory_put,
            "memory_search": memory.memory_search,
            "memory_get_latest": memory.memory_get_latest,
        }

    def execute(self, tool_call: ToolCall) -> Any:
        """Execute a single tool call. Returns the tool's result.

        Raises ToolExecutionError if the tool fails.
        """
        name = tool_call.tool_name.value
        fn = self._tools.get(name)
        if fn is None:
            raise ToolExecutionError(f"Unknown tool: {name}")

        logger.info("Executing tool: %s args=%s", name, tool_call.args)
        try:
            return fn(**tool_call.args)
        except TypeError as e:
            raise ToolExecutionError(f"Bad args for {name}: {e}") from e
        except Exception as e:
            raise ToolExecutionError(f"Tool {name} failed: {e}") from e

    def execute_all(self, tool_calls: list[ToolCall]) -> list[dict[str, Any]]:
        """Execute tool calls in order. Returns a list of result dicts.

        Each result dict has: tool_name, args, success, result (or error).
        Continues executing remaining tools even if one fails.
        """
        results = []
        for tc in tool_calls:
            entry: dict[str, Any] = {
                "tool_name": tc.tool_name.value,
                "args": tc.args,
            }
            try:
                entry["result"] = self.execute(tc)
                entry["success"] = True
            except ToolExecutionError as e:
                logger.error("Tool %s failed: %s", tc.tool_name.value, e)
                entry["error"] = str(e)
                entry["success"] = False
            results.append(entry)
        return results
