"""Tests for the CloudCode plan schema validation."""

import json

import pytest
from pydantic import ValidationError

from src.runner.plan_schema import ExecutionPlan, ToolCall, ToolName


class TestToolCall:
    def test_valid_tool_call(self):
        tc = ToolCall(tool_name="telegram_send_message", args={"chat_id": "c1", "text": "hi"})
        assert tc.tool_name == ToolName.TELEGRAM_SEND_MESSAGE
        assert tc.args == {"chat_id": "c1", "text": "hi"}

    def test_all_tool_names(self):
        for name in ["telegram_send_message", "memory_put", "memory_search", "memory_get_latest"]:
            tc = ToolCall(tool_name=name, args={})
            assert tc.tool_name.value == name

    def test_invalid_tool_name_rejected(self):
        with pytest.raises(ValidationError):
            ToolCall(tool_name="unknown_tool", args={})

    def test_default_empty_args(self):
        tc = ToolCall(tool_name="memory_get_latest")
        assert tc.args == {}


class TestExecutionPlan:
    def test_minimal_valid_plan(self):
        plan = ExecutionPlan()
        assert plan.assistant_message == ""
        assert plan.tool_calls == []
        assert plan.state_patch == {}
        assert plan.notes == ""

    def test_full_plan(self):
        plan = ExecutionPlan(
            assistant_message="thinking...",
            tool_calls=[
                {"tool_name": "memory_put", "args": {"text": "note", "tags": ["t1"]}},
                {"tool_name": "telegram_send_message", "args": {"chat_id": "c1", "text": "done"}},
            ],
            state_patch={"last_topic": "test"},
            notes="logged",
        )
        assert len(plan.tool_calls) == 2
        assert plan.tool_calls[0].tool_name == ToolName.MEMORY_PUT
        assert plan.tool_calls[1].tool_name == ToolName.TELEGRAM_SEND_MESSAGE
        assert plan.state_patch == {"last_topic": "test"}
        assert plan.notes == "logged"

    def test_from_json_string(self):
        raw = json.dumps({
            "assistant_message": "hello",
            "tool_calls": [
                {"tool_name": "telegram_send_message", "args": {"chat_id": "local-test", "text": "hi"}}
            ],
            "state_patch": {},
            "notes": "",
        })
        plan = ExecutionPlan.model_validate_json(raw)
        assert plan.assistant_message == "hello"
        assert len(plan.tool_calls) == 1

    def test_invalid_tool_in_plan_rejected(self):
        with pytest.raises(ValidationError):
            ExecutionPlan(
                tool_calls=[{"tool_name": "bad_tool", "args": {}}],
            )

    def test_extra_fields_ignored(self):
        """CloudCode might return extra fields — they should not break parsing."""
        data = {
            "assistant_message": "ok",
            "tool_calls": [],
            "state_patch": {},
            "notes": "",
            "extra_field": "should be ignored",
        }
        plan = ExecutionPlan.model_validate(data)
        assert plan.assistant_message == "ok"

    def test_roundtrip_serialization(self):
        plan = ExecutionPlan(
            assistant_message="test",
            tool_calls=[
                ToolCall(tool_name=ToolName.MEMORY_SEARCH, args={"query": "pref", "k": 3}),
            ],
            state_patch={"count": 1},
        )
        data = json.loads(plan.model_dump_json())
        plan2 = ExecutionPlan.model_validate(data)
        assert plan2.assistant_message == plan.assistant_message
        assert len(plan2.tool_calls) == 1
        assert plan2.tool_calls[0].args["query"] == "pref"
