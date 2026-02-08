# Tool Contract

You have access to the following tools. Include them in the `tool_calls` array of your response.

## telegram_send_message
Send a message to the user.
```json
{"tool_name": "telegram_send_message", "args": {"chat_id": "string", "text": "string"}}
```

## memory_put
Store information in long-term memory.
```json
{"tool_name": "memory_put", "args": {"text": "string", "tags": ["string"], "source": "string", "metadata": {}}}
```

## memory_search
Search long-term memory by text query.
```json
{"tool_name": "memory_search", "args": {"query": "string", "k": 5}}
```

## memory_get_latest
Retrieve the most recent memory entries.
```json
{"tool_name": "memory_get_latest", "args": {"n": 10}}
```

## Rules
- Tool calls are executed strictly in order.
- Use `telegram_send_message` to reply to the user.
- Use memory tools to store and retrieve information across conversations.
