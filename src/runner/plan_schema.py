"""Plan Schema — Pydantic models for CloudCode output.

Defines the structured JSON schema that CloudCode must return:
- assistant_message: text reply to the user
- tool_calls: ordered list of tool invocations
- state_patch: partial update to agent_state.json
- notes: optional, for logs only
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ToolName(str, Enum):
    TELEGRAM_SEND_MESSAGE = "telegram_send_message"
    MEMORY_PUT = "memory_put"
    MEMORY_SEARCH = "memory_search"
    MEMORY_GET_LATEST = "memory_get_latest"


class ToolCall(BaseModel):
    tool_name: ToolName
    args: dict[str, Any] = Field(default_factory=dict)


class ExecutionPlan(BaseModel):
    assistant_message: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    state_patch: dict[str, Any] = Field(default_factory=dict)
    notes: str = ""
