"""CloudCode Bridge — invokes CloudCode CLI and parses structured JSON responses.

Prepares the prompt pack (system context, tool contract, output format, examples)
along with the current user message, transcript, and agent state.
Returns a validated execution plan.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Any

from src.runner.plan_schema import ExecutionPlan

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path("src/cloudcode_prompts")

PROMPT_FILES = [
    "system_context.md",
    "tool_contract.md",
    "output_format.md",
    "examples.md",
]


class CloudCodeError(Exception):
    """Raised when CloudCode invocation or parsing fails."""


class CloudCodeBridge:
    """Invokes the Claude CLI and returns a validated ExecutionPlan."""

    def __init__(
        self,
        model: str = "haiku",
        timeout_seconds: int = 30,
        prompts_dir: Path | str = PROMPTS_DIR,
    ):
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.prompts_dir = Path(prompts_dir)
        self._prompt_pack = self._load_prompt_pack()

    def invoke(
        self,
        user_message: str,
        chat_id: str = "local-test",
        transcript: list[dict[str, Any]] | None = None,
        agent_state: dict[str, Any] | None = None,
    ) -> ExecutionPlan:
        """Build prompt, call Claude CLI, parse and return an ExecutionPlan.

        Raises CloudCodeError on CLI failure or unparseable output.
        """
        prompt = self._build_prompt(
            user_message=user_message,
            chat_id=chat_id,
            transcript=transcript or [],
            agent_state=agent_state or {},
        )

        raw_output = self._call_cli(prompt)
        return self._parse_response(raw_output)

    def _load_prompt_pack(self) -> str:
        """Read and concatenate all prompt files."""
        parts = []
        for filename in PROMPT_FILES:
            path = self.prompts_dir / filename
            if path.exists():
                parts.append(path.read_text().strip())
            else:
                logger.warning("Prompt file not found: %s", path)
        return "\n\n---\n\n".join(parts)

    def _build_prompt(
        self,
        user_message: str,
        chat_id: str,
        transcript: list[dict[str, Any]],
        agent_state: dict[str, Any],
    ) -> str:
        """Assemble the full prompt from prompt pack + runtime context."""
        sections = [self._prompt_pack]

        sections.append(
            "# Current Context\n\n"
            f"**chat_id:** {chat_id}\n\n"
            f"**agent_state:**\n```json\n{json.dumps(agent_state, indent=2)}\n```"
        )

        if transcript:
            transcript_text = json.dumps(transcript, indent=2)
            sections.append(
                f"# Recent Transcript\n\n```json\n{transcript_text}\n```"
            )

        sections.append(
            f"# User Message\n\n{user_message}\n\n"
            "Respond with strict JSON only."
        )

        return "\n\n---\n\n".join(sections)

    def _call_cli(self, prompt: str) -> str:
        """Invoke the Claude CLI with the assembled prompt."""
        cmd = [
            "claude",
            "-p", prompt,
            "--model", self.model,
            "--no-input",
        ]
        logger.debug("Calling CloudCode CLI (model=%s, timeout=%ds)", self.model, self.timeout_seconds)
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except FileNotFoundError:
            raise CloudCodeError(
                "claude CLI not found. Is Claude Code installed and on PATH?"
            )
        except subprocess.TimeoutExpired:
            raise CloudCodeError(
                f"CloudCode CLI timed out after {self.timeout_seconds}s"
            )

        if result.returncode != 0:
            raise CloudCodeError(
                f"CloudCode CLI exited with code {result.returncode}: {result.stderr.strip()}"
            )

        output = result.stdout.strip()
        if not output:
            raise CloudCodeError("CloudCode CLI returned empty output")

        return output

    @staticmethod
    def _parse_response(raw: str) -> ExecutionPlan:
        """Extract JSON from the raw CLI output and validate against the schema.

        Handles responses that may be wrapped in markdown code fences.
        """
        # Try to extract JSON from markdown code block
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", raw, re.DOTALL)
        json_str = match.group(1).strip() if match else raw.strip()

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise CloudCodeError(f"Failed to parse JSON from CloudCode output: {e}\nRaw output:\n{raw}")

        try:
            return ExecutionPlan.model_validate(data)
        except Exception as e:
            raise CloudCodeError(f"CloudCode output failed schema validation: {e}\nParsed data:\n{data}")
