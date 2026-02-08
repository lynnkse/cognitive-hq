"""Tests for the CloudCode bridge — prompt assembly and response parsing."""

import json

import pytest

from src.runner.cloudcode_bridge import CloudCodeBridge, CloudCodeError
from src.runner.plan_schema import ToolName


@pytest.fixture
def bridge(tmp_path):
    """Create a bridge with prompt files in a temp directory."""
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "system_context.md").write_text("You are an agent.")
    (prompts / "tool_contract.md").write_text("Tools: telegram_send_message, memory_put")
    (prompts / "output_format.md").write_text("Respond with JSON.")
    (prompts / "examples.md").write_text("Example: {}")
    return CloudCodeBridge(prompts_dir=prompts)


class TestBuildPrompt:
    def test_contains_prompt_pack(self, bridge):
        prompt = bridge._build_prompt("hi", "c1", [], {})
        assert "You are an agent." in prompt
        assert "Tools:" in prompt
        assert "Respond with JSON." in prompt

    def test_contains_user_message(self, bridge):
        prompt = bridge._build_prompt("hello world", "c1", [], {})
        assert "hello world" in prompt

    def test_contains_chat_id(self, bridge):
        prompt = bridge._build_prompt("hi", "my-chat", [], {})
        assert "my-chat" in prompt

    def test_contains_agent_state(self, bridge):
        prompt = bridge._build_prompt("hi", "c1", [], {"mood": "happy"})
        assert '"mood": "happy"' in prompt

    def test_contains_transcript_when_provided(self, bridge):
        transcript = [{"role": "user", "text": "prev msg"}]
        prompt = bridge._build_prompt("hi", "c1", transcript, {})
        assert "prev msg" in prompt

    def test_omits_transcript_section_when_empty(self, bridge):
        prompt = bridge._build_prompt("hi", "c1", [], {})
        assert "Recent Transcript" not in prompt


class TestParseResponse:
    def test_plain_json(self):
        raw = json.dumps({
            "assistant_message": "ok",
            "tool_calls": [],
            "state_patch": {},
            "notes": "",
        })
        plan = CloudCodeBridge._parse_response(raw)
        assert plan.assistant_message == "ok"

    def test_json_in_code_fence(self):
        raw = '```json\n{"assistant_message":"ok","tool_calls":[],"state_patch":{},"notes":""}\n```'
        plan = CloudCodeBridge._parse_response(raw)
        assert plan.assistant_message == "ok"

    def test_json_in_bare_code_fence(self):
        raw = '```\n{"assistant_message":"ok","tool_calls":[],"state_patch":{}}\n```'
        plan = CloudCodeBridge._parse_response(raw)
        assert plan.assistant_message == "ok"

    def test_with_tool_calls(self):
        raw = json.dumps({
            "assistant_message": "storing",
            "tool_calls": [
                {"tool_name": "memory_put", "args": {"text": "note", "tags": ["a"]}},
                {"tool_name": "telegram_send_message", "args": {"chat_id": "c1", "text": "done"}},
            ],
            "state_patch": {"count": 1},
            "notes": "test",
        })
        plan = CloudCodeBridge._parse_response(raw)
        assert len(plan.tool_calls) == 2
        assert plan.tool_calls[0].tool_name == ToolName.MEMORY_PUT
        assert plan.tool_calls[1].args["text"] == "done"
        assert plan.state_patch == {"count": 1}

    def test_invalid_json_raises(self):
        with pytest.raises(CloudCodeError, match="Failed to parse JSON"):
            CloudCodeBridge._parse_response("not json at all")

    def test_invalid_schema_raises(self):
        raw = json.dumps({"tool_calls": [{"tool_name": "bad_tool", "args": {}}]})
        with pytest.raises(CloudCodeError, match="failed schema validation"):
            CloudCodeBridge._parse_response(raw)

    def test_json_with_surrounding_text(self):
        """If CloudCode wraps JSON in prose, code fence extraction handles it."""
        raw = 'Here is my response:\n```json\n{"assistant_message":"hi","tool_calls":[],"state_patch":{}}\n```\nDone.'
        plan = CloudCodeBridge._parse_response(raw)
        assert plan.assistant_message == "hi"
