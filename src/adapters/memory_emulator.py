"""Memory Emulator — JSONL-based long-term storage.

API:
- memory_put(text, tags, source, metadata)
- memory_search(query, k)
- memory_get_latest(n)

Current implementation uses naive text matching.
Later replaced by a vector DB adapter.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from src.runner.time_utils import utc_now

DEFAULT_STORE_PATH = Path("state/memory/memory_store.jsonl")


class MemoryEmulator:
    """JSONL-backed long-term memory store."""

    def __init__(self, store_path: Path | str = DEFAULT_STORE_PATH):
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)

    def memory_put(
        self,
        text: str,
        tags: list[str] | None = None,
        source: str = "conversation",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Append a memory record to the JSONL store. Returns the record."""
        record = {
            "ts": utc_now(),
            "id": str(uuid.uuid4()),
            "text": text,
            "tags": tags or [],
            "source": source,
            "metadata": metadata or {},
        }
        with open(self.store_path, "a") as f:
            f.write(json.dumps(record) + "\n")
        return record

    def memory_search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """Search memory by naive case-insensitive text matching.

        Scores each record by the number of query terms found in its text + tags.
        Returns the top k results sorted by score descending, then recency.
        """
        records = self._load_all()
        if not records:
            return []

        query_terms = query.lower().split()
        scored: list[tuple[int, int, dict]] = []
        for i, rec in enumerate(records):
            searchable = (rec["text"] + " " + " ".join(rec["tags"])).lower()
            score = sum(1 for term in query_terms if term in searchable)
            if score > 0:
                scored.append((score, i, rec))

        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return [rec for _, _, rec in scored[:k]]

    def memory_get_latest(self, n: int = 10) -> list[dict[str, Any]]:
        """Return the n most recent memory records (newest first)."""
        records = self._load_all()
        return list(reversed(records[-n:]))

    def _load_all(self) -> list[dict[str, Any]]:
        """Load all records from the JSONL store."""
        if not self.store_path.exists():
            return []
        records = []
        with open(self.store_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records
