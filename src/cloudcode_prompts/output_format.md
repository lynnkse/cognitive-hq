# Output Format

You MUST respond with strict JSON only. No prose outside the JSON object.

```json
{
  "assistant_message": "Your internal reasoning or empty string",
  "tool_calls": [
    {"tool_name": "tool_name_here", "args": {}}
  ],
  "state_patch": {},
  "notes": "Optional notes for logs only"
}
```

## Fields

- **assistant_message** (string, required): Your reasoning or message. Can be empty.
- **tool_calls** (array, required): Ordered list of tool invocations. Can be empty `[]`.
- **state_patch** (object, required): Partial update merged into agent_state.json. Can be empty `{}`.
- **notes** (string, optional): For logging purposes only. Not shown to the user.
