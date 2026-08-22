from intentfence_contracts import DecisionType
from state_testkit import make_context

from intentfence_state import (
    IntentDriftSignal,
    NullDriftSignal,
    PassthroughDriftSignal,
    chain_tools,
    external_transfer_in_chain,
    parse_chain_entries,
    record_action,
    secret_access_in_chain,
)


def test_parse_chain_entries_splits_tool_and_decision():
    entries = parse_chain_entries(["browse_web:ALLOW", "read_file:BLOCK"])
    assert entries == [("browse_web", "ALLOW"), ("read_file", "BLOCK")]


def test_parse_chain_entries_ignores_malformed_rows():
    assert parse_chain_entries(["garbage", ":ALLOW", "write_file:ALLOW"]) == [
        ("write_file", "ALLOW")
    ]


def test_chain_tools_extracts_tool_names():
    assert chain_tools(["a:ALLOW", "b:BLOCK"]) == ["a", "b"]


def test_secret_access_detected_from_flag():
    context = make_context(secret_accessed=True)
    assert secret_access_in_chain(context) is True


def test_secret_access_detected_from_chain_when_flag_missing():
    context = make_context(recent_action_chain=["read_file:ALLOW"], secret_accessed=False)
    assert secret_access_in_chain(context) is True


def test_clean_session_has_no_secret_evidence():
    context = make_context(recent_action_chain=["browse_web:ALLOW", "write_file:ALLOW"])
    assert secret_access_in_chain(context) is False


def test_external_transfer_detection_covers_network_and_message():
    network = make_context(recent_tools=["http_request"])
    message = make_context(recent_tools=["send_message"])
    safe = make_context(recent_tools=["browse_web", "write_file"])
    assert external_transfer_in_chain(network) is True
    assert external_transfer_in_chain(message) is True
    assert external_transfer_in_chain(safe) is False


def test_passthrough_drift_signal_returns_context_score():
    signal = PassthroughDriftSignal()
    context = make_context(intent_drift_score=0.4)
    assert signal.score(None, None, context) == 0.4


def test_null_drift_signal_returns_zero():
    assert NullDriftSignal().score(None, None, make_context()) == 0.0


def test_custom_drift_signal_can_implement_the_interface():
    class FixedDriftSignal(IntentDriftSignal):
        def score(self, request, contract, context) -> float:
            return 0.3

    assert FixedDriftSignal().score(None, None, make_context()) == 0.3


def test_record_action_chain_entry_uses_decision_value():
    updated = record_action(
        make_context(),
        tool="send_message",
        decision=DecisionType.REQUIRE_APPROVAL,
        now=None,
    )
    assert "send_message:REQUIRE_APPROVAL" in updated.recent_action_chain
