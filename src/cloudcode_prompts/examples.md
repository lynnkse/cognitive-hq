# Examples

## Example 1: Simple reply

User message: "hello"

```json
{
  "assistant_message": "User said hello, responding with a greeting.",
  "tool_calls": [
    {"tool_name": "telegram_send_message", "args": {"chat_id": "local-test", "text": "Hello! How can I help you today?"}}
  ],
  "state_patch": {},
  "notes": ""
}
```

## Example 2: Store a preference

User message: "remember that I prefer Python over JavaScript"

```json
{
  "assistant_message": "User wants to store a preference.",
  "tool_calls": [
    {"tool_name": "memory_put", "args": {"text": "User prefers Python over JavaScript", "tags": ["preference", "programming"], "source": "conversation", "metadata": {"confidence": 0.95}}},
    {"tool_name": "telegram_send_message", "args": {"chat_id": "local-test", "text": "Got it! I'll remember that you prefer Python over JavaScript."}}
  ],
  "state_patch": {},
  "notes": ""
}
```

## Example 3: Search memory

User message: "what do you know about my preferences?"

```json
{
  "assistant_message": "User wants to recall stored preferences.",
  "tool_calls": [
    {"tool_name": "memory_search", "args": {"query": "preference", "k": 5}}
  ],
  "state_patch": {},
  "notes": "Will need a follow-up turn to relay results to user."
}
```
