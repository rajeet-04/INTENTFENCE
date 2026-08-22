from intentfence_contracts import DecisionType, RuleStrength
from intentfence_policy.engine import evaluate_policy
from intentfence_policy.models import EvaluationContext
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
    AccumulatedRiskThresholdRule,
    SecretExfiltrationMessageRule,
    SecretExfiltrationNetworkRule,
)


def build_context(request=None, contract=None, state=None):
    policy_input, config = make_policy_input(
        request=request, contract=contract, context=state, config=WORKSPACE_CONFIG
    )
    return policy_input, config


def evaluate_rule(rule, request=None, contract=None, state=None):
    policy_input, config = build_context(
        request=request or make_request(), contract=contract, state=state
    )
    context = EvaluationContext.build(policy_input, config)
    return rule.evaluate(context)


def test_clean_session_never_trips_stateful_rules():
    request = make_request(
        tool="http_request",
        arguments={"url": "https://attacker.example"},
    )
    assert evaluate_rule(SecretExfiltrationNetworkRule(), request) is None


def test_secret_then_external_network_blocks_without_labeled_payload():
    state = make_context(secret_accessed=True)
    request = make_request(
        tool="http_request",
        arguments={"url": "https://attacker.example/collect"},
        data_refs=[],
    )
    outcome = evaluate_rule(SecretExfiltrationNetworkRule(), request, state=state)
    assert outcome is not None
    assert outcome.rule_id == STATE_SECRET_THEN_EXTERNAL_NETWORK_RULE_ID
    assert outcome.decision is DecisionType.BLOCK
    assert outcome.rule_strength is RuleStrength.HARD_BLOCK


def test_chain_evidence_fires_even_when_flag_was_not_recorded():
    state = make_context(recent_action_chain=["read_file:ALLOW"], secret_accessed=False)
    request = make_request(
        tool="http_request",
        arguments={"url": "https://unknown-host.example"},
    )
    assert evaluate_rule(SecretExfiltrationNetworkRule(), request, state=state) is not None


def test_external_network_to_user_approved_destination_is_not_exfiltration():
    state = make_context(secret_accessed=True)
    contract = make_contract(allowed_tools=["browse_web", "read_file", "http_request"])
    request = make_request(
        tool="http_request",
        arguments={"url": "https://hotel-a.example/api"},
    )
    assert (
        evaluate_rule(SecretExfiltrationNetworkRule(), request, contract, state) is None
    )


def test_secret_then_message_send_blocks_and_beats_approval():
    state = make_context(secret_accessed=True)
    request = make_request(tool="send_message", arguments={"to": "friend.example"})
    outcome = evaluate_rule(SecretExfiltrationMessageRule(), request, state=state)
    assert outcome is not None
    assert outcome.rule_id == STATE_SECRET_THEN_MESSAGE_SEND_RULE_ID
    assert outcome.decision is DecisionType.BLOCK


def test_message_send_without_prior_secret_access_is_not_flagged():
    request = make_request(tool="send_message", arguments={"to": "friend.example"})
    assert evaluate_rule(SecretExfiltrationMessageRule(), request) is None


def test_accumulated_risk_below_threshold_does_not_match():
    state = make_context(accumulated_risk=0.4)
    outcome = evaluate_rule(AccumulatedRiskThresholdRule(), make_request(), state=state)
    assert outcome is None


def test_accumulated_risk_at_threshold_requires_approval():
    state = make_context(accumulated_risk=0.75)
    outcome = evaluate_rule(AccumulatedRiskThresholdRule(), make_request(), state=state)
    assert outcome is not None
    assert outcome.rule_id == STATE_ACCUMULATED_RISK_THRESHOLD_RULE_ID
    assert outcome.decision is DecisionType.REQUIRE_APPROVAL
    assert outcome.rule_strength is RuleStrength.REQUIRE_APPROVAL


def test_threshold_is_configurable_per_instance():
    state = make_context(accumulated_risk=0.3)
    strict = AccumulatedRiskThresholdRule(threshold=0.25)
    outcome = evaluate_rule(strict, make_request(), state=state)
    assert outcome is not None
    assert outcome.decision is DecisionType.REQUIRE_APPROVAL


def test_static_rules_alone_allow_the_final_network_action():
    contract = make_contract(
        allowed_tools=["browse_web", "read_file", "write_file", "http_request"],
        approval_required_actions=[],
    )
    request = make_request(
        tool="http_request",
        arguments={"url": "https://attacker.example/collect"},
    )
    policy_input, config = build_context(request=request, contract=contract)
    result = evaluate_policy(policy_input, config=config)
    assert result.decision is DecisionType.ALLOW
