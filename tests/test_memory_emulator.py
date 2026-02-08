"""Tests for the memory emulator adapter."""

import json
import tempfile
from pathlib import Path

import pytest

from src.adapters.memory_emulator import MemoryEmulator


@pytest.fixture
def mem(tmp_path):
    """Create a MemoryEmulator backed by a temp file."""
    return MemoryEmulator(store_path=tmp_path / "memory" / "store.jsonl")


class TestMemoryPut:
    def test_creates_record_with_required_fields(self, mem):
        rec = mem.memory_put("hello world")
        assert rec["text"] == "hello world"
        assert rec["tags"] == []
        assert rec["source"] == "conversation"
        assert rec["metadata"] == {}
        assert "ts" in rec
        assert "id" in rec

    def test_custom_tags_source_metadata(self, mem):
        rec = mem.memory_put(
            "user likes Python",
            tags=["preference", "lang"],
            source="manual",
            metadata={"confidence": 0.9},
        )
        assert rec["tags"] == ["preference", "lang"]
        assert rec["source"] == "manual"
        assert rec["metadata"] == {"confidence": 0.9}

    def test_appends_to_jsonl_file(self, mem):
        mem.memory_put("first")
        mem.memory_put("second")
        lines = mem.store_path.read_text().strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["text"] == "first"
        assert json.loads(lines[1])["text"] == "second"

    def test_unique_ids(self, mem):
        r1 = mem.memory_put("a")
        r2 = mem.memory_put("b")
        assert r1["id"] != r2["id"]


class TestMemoryGetLatest:
    def test_empty_store(self, mem):
        assert mem.memory_get_latest() == []

    def test_returns_newest_first(self, mem):
        mem.memory_put("first")
        mem.memory_put("second")
        mem.memory_put("third")
        results = mem.memory_get_latest(n=2)
        assert len(results) == 2
        assert results[0]["text"] == "third"
        assert results[1]["text"] == "second"

    def test_n_larger_than_store(self, mem):
        mem.memory_put("only one")
        results = mem.memory_get_latest(n=100)
        assert len(results) == 1


class TestMemorySearch:
    def test_empty_store(self, mem):
        assert mem.memory_search("anything") == []

    def test_finds_matching_text(self, mem):
        mem.memory_put("user prefers Python")
        mem.memory_put("weather is sunny")
        mem.memory_put("Python is great for scripting")
        results = mem.memory_search("Python")
        assert len(results) == 2
        texts = [r["text"] for r in results]
        assert "user prefers Python" in texts
        assert "Python is great for scripting" in texts

    def test_case_insensitive(self, mem):
        mem.memory_put("User likes PYTHON")
        results = mem.memory_search("python")
        assert len(results) == 1

    def test_searches_tags_too(self, mem):
        mem.memory_put("some note", tags=["programming", "python"])
        results = mem.memory_search("python")
        assert len(results) == 1

    def test_respects_k_limit(self, mem):
        for i in range(10):
            mem.memory_put(f"python note {i}")
        results = mem.memory_search("python", k=3)
        assert len(results) == 3

    def test_multi_term_scoring(self, mem):
        mem.memory_put("python is a language")
        mem.memory_put("python scripting is fast")
        results = mem.memory_search("python scripting")
        # "python scripting is fast" matches both terms -> higher score -> first
        assert results[0]["text"] == "python scripting is fast"

    def test_no_match_returns_empty(self, mem):
        mem.memory_put("hello world")
        results = mem.memory_search("zzzznotfound")
        assert results == []
