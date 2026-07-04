"""Unit tests for stage1 intent classification — the pipeline's front door.

The README's core architectural claim is "classify before you retrieve":
these tests pin the routing behavior of classify_message_intent with the
Anthropic client faked at the module boundary.
"""

from types import SimpleNamespace
from typing import Any, Dict

import pytest

import assistant.flows.node_logic.stage1_intent_router as stage1
from assistant.flows.node_logic.stage0_session_management import (
    initialize_conversation_state,
)


class FakeAnthropic:
    canned_response = "knowledge_query|neutral"
    raise_error = False

    def __init__(self, api_key: str = None):
        self.messages = self

    def create(self, **kwargs):
        if FakeAnthropic.raise_error:
            raise RuntimeError("simulated API outage")
        return SimpleNamespace(
            content=[SimpleNamespace(text=FakeAnthropic.canned_response)]
        )


@pytest.fixture(autouse=True)
def fake_client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(stage1, "Anthropic", FakeAnthropic)
    FakeAnthropic.canned_response = "knowledge_query|neutral"
    FakeAnthropic.raise_error = False


def _state(query: str, chat_history=None) -> Dict[str, Any]:
    state = {
        "role": "Learn more about Noah",
        "query": query,
        "chat_history": chat_history
        or [
            {"role": "user", "content": "1"},
            {"role": "assistant", "content": "Welcome — what brings you here?"},
        ],
        "session_memory": {},
    }
    result = initialize_conversation_state(state)
    state.update(result or {})
    state["query"] = query  # init must not eat the query
    return state


def _classify(state: Dict[str, Any]) -> Dict[str, Any]:
    # stage1.classify_intent is re-exported by the node hub as
    # classify_message_intent — this is the node the pipeline runs.
    result = stage1.classify_intent(state)
    state.update(result or {})
    return state


def test_knowledge_query_proceeds_to_rag():
    state = _classify(_state("What projects has Noah built?"))
    assert state["message_intent"] == "knowledge_query"
    assert state["skip_rag"] is False


@pytest.mark.parametrize(
    "canned,expected_intent",
    [
        ("crush_confession|crush", "crush_confession"),
        ("greeting|casual", "greeting"),
        ("small_talk|casual", "small_talk"),
        ("off_topic|neutral", "off_topic"),
    ],
)
def test_non_knowledge_intents_skip_rag(canned, expected_intent):
    FakeAnthropic.canned_response = canned
    state = _classify(_state("some visitor message"))
    assert state["message_intent"] == expected_intent
    assert state["skip_rag"] is True


def test_invalid_intent_defaults_to_knowledge_query():
    """An off-vocabulary classifier answer must fail safe, not crash."""
    FakeAnthropic.canned_response = "banana|weird"
    state = _classify(_state("tell me about the pipeline"))
    assert state["message_intent"] == "knowledge_query"
    assert state["skip_rag"] is False


def test_missing_visitor_signal_is_tolerated():
    """Single-field responses (no pipe) must still parse the intent."""
    FakeAnthropic.canned_response = "knowledge_query"
    state = _classify(_state("what does Noah do at Tesla?"))
    assert state["message_intent"] == "knowledge_query"
    assert state["skip_rag"] is False


def test_classifier_outage_fails_open_to_knowledge_query():
    """If the LLM call dies, the visitor still gets a RAG answer."""
    FakeAnthropic.raise_error = True
    state = _classify(_state("what is Noah's background?"))
    assert state["message_intent"] == "knowledge_query"
    assert state["skip_rag"] is False
