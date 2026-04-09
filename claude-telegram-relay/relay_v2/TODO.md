# Relay v2 — Dev TODO

## Pending

- [ ] **Full response delivery after multi-step tasks** — After long runs (log + commit + multiple permissions), the final text response sometimes never appears in Telegram. Either the JSONL debounce window is too short for slow multi-tool responses, or the response times out. Need to investigate: check if final text entry is written to JSONL after long tool chains, tune debounce/timeout, and ensure the complete summary response (not just tool confirmations) reaches the user.

- [ ] **Message source metadata in responses** — Claude should know whether a message came from Telegram or CLI (or which CLI user, future multi-user). The `source` field already flows through QueueItem and is published with each response; expose it to the Claude prompt so it can tailor its reply (e.g. keep responses concise for Telegram, can be verbose for CLI). Consider injecting source into the PTY message prefix: `[from:telegram] user message here`.

## Done

- [x] Permission deadlock via PermissionRequest hook (concurrent_updates fix)
- [x] JSONL-based response detection
- [x] TelegramNode inline Allow/Deny buttons for permission requests
