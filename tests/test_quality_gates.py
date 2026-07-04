"""Unit tests for the retrieval/generation quality gates.

These cover the checks the project's documentation actually advertises:
grounding validation (similarity threshold gate before generation),
conversation-phase tracking, and verbatim-copy detection.
"""

from typing import Any, Dict

import pytest

from assistant.flows.node_logic.stage4_retrieval_nodes import validate_grounding
from assistant.flows.node_logic.stage5_generation_nodes import (
    _detect_verbatim_copying,
)
from assistant.flows.node_logic.stage5_quality_validation import (
    detect_conversation_phase,
)


def _merged(state: Dict[str, Any], result) -> Dict[str, Any]:
    state.update(result or {})
    return state


class TestValidateGrounding:
    def test_high_similarity_is_ok(self):
        state = {"retrieval_scores": [0.92, 0.85, 0.78], "retrieved_chunks": [{}]}
        state = _merged(state, validate_grounding(state, threshold=0.45))
        assert state["grounding_status"] == "ok"

    def test_low_similarity_is_insufficient(self):
        state = {"retrieval_scores": [0.38, 0.32], "retrieved_chunks": [{}]}
        state = _merged(state, validate_grounding(state, threshold=0.45))
        assert state["grounding_status"] == "insufficient"

    def test_no_results(self):
        state = {"retrieval_scores": [], "retrieved_chunks": []}
        state = _merged(state, validate_grounding(state, threshold=0.45))
        assert state["grounding_status"] == "no_results"

    def test_threshold_is_a_real_knob(self):
        """The same scores pass a lenient gate and fail a strict one."""
        scores = {"retrieval_scores": [0.40], "retrieved_chunks": [{}]}
        lenient = _merged(dict(scores), validate_grounding(dict(scores), threshold=0.30))
        strict = _merged(dict(scores), validate_grounding(dict(scores), threshold=0.50))
        assert lenient["grounding_status"] == "ok"
        assert strict["grounding_status"] == "insufficient"


class TestConversationPhase:
    @pytest.mark.parametrize(
        "turn,topics,expected",
        [
            (1, [], "discovery"),
            (3, ["a"], "discovery"),
            (5, ["a", "b"], "exploration"),
            (9, ["a", "b", "c", "d"], "synthesis"),
            (16, [], "extended"),
        ],
    )
    def test_phase_buckets(self, turn, topics, expected):
        state = {
            "conversation_turn": turn,
            "session_memory": {"topics": topics},
        }
        state = _merged(state, detect_conversation_phase(state))
        assert state["conversation_phase"] == expected


class TestVerbatimDetection:
    CHUNK = {
        "content": (
            "Noah built a functional pipeline with pgvector semantic search "
            "and deterministic side effect execution for production use."
        ),
        "section": "architecture",
    }

    def test_verbatim_copy_is_detected(self):
        answer = (
            "Great question. Noah built a functional pipeline with pgvector "
            "semantic search and deterministic side effect execution."
        )
        result = _detect_verbatim_copying(answer, [self.CHUNK])
        assert result["has_verbatim_copying"] is True

    def test_synthesized_answer_passes(self):
        answer = (
            "The system searches a vector database first, then generates a "
            "grounded reply — actions fire from a state machine, not the model."
        )
        result = _detect_verbatim_copying(answer, [self.CHUNK])
        assert result["has_verbatim_copying"] is False

    def test_citation_phrases_are_flagged(self):
        answer = "According to the context, Noah works at Tesla."
        result = _detect_verbatim_copying(answer, [self.CHUNK])
        assert result["has_citation_phrases"] is True
        assert result["detected_phrases"]
