"""Unit tests for PgVectorRetriever threshold plumbing.

Hermetic: the OpenAI embed step and the Supabase RPC are both faked, so
these verify what the retriever sends to `match_kb_chunks` and how it maps
results — the exact behavior the README documents (0.50 strict default,
overridable threshold, empty-result handling).
"""

from typing import Any, Dict, List

import pytest

from assistant.retrieval.pgvector_retriever import PgVectorRetriever


class FakeRpcResult:
    def __init__(self, data):
        self.data = data

    def execute(self):
        return self


class FakeSupabase:
    def __init__(self, data: List[Dict[str, Any]]):
        self._data = data
        self.calls: List[Dict[str, Any]] = []

    def rpc(self, fn_name: str, params: Dict[str, Any]):
        self.calls.append({"fn": fn_name, "params": params})
        return FakeRpcResult(self._data)


@pytest.fixture
def retriever(monkeypatch: pytest.MonkeyPatch) -> PgVectorRetriever:
    r = PgVectorRetriever()
    monkeypatch.setattr(r, "embed", lambda text: [0.1] * 1536)
    return r


def _wire(retriever: PgVectorRetriever, data: List[Dict[str, Any]]) -> FakeSupabase:
    fake = FakeSupabase(data)
    retriever.supabase_client = fake
    return fake


def test_default_threshold_is_strict_050(retriever):
    fake = _wire(retriever, [{"content": "x", "similarity": 0.9}])
    retriever.retrieve("what did noah build?")

    call = fake.calls[0]
    assert call["fn"] == "match_kb_chunks"
    assert call["params"]["match_threshold"] == pytest.approx(0.50)


def test_threshold_override_reaches_the_rpc(retriever):
    """The 0.30 fallback works by passing a lower threshold through."""
    fake = _wire(retriever, [{"content": "x", "similarity": 0.35}])
    retriever.retrieve("broad query", threshold=0.30)

    assert fake.calls[0]["params"]["match_threshold"] == pytest.approx(0.30)


def test_empty_rpc_result_returns_empty_list(retriever):
    _wire(retriever, [])
    assert retriever.retrieve("nothing matches this") == []


def test_chunks_are_returned_as_given(retriever):
    rows = [
        {"content": "chunk a", "similarity": 0.91, "section": "career"},
        {"content": "chunk b", "similarity": 0.72, "section": "projects"},
    ]
    _wire(retriever, rows)
    assert retriever.retrieve("noah career") == rows


def test_empty_embedding_short_circuits(retriever, monkeypatch):
    """No embedding → no RPC call, empty result (fail quiet, not crash)."""
    fake = _wire(retriever, [{"content": "x", "similarity": 0.9}])
    monkeypatch.setattr(retriever, "embed", lambda text: [])
    assert retriever.retrieve("query") == []
    assert fake.calls == []
