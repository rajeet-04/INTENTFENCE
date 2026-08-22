from intentfence_contracts import DecisionType, DestinationClass, RuleStrength, Sensitivity

from intentfence_dataflow import evaluate_flow, normalize_destination

HOTEL_OBJECTIVE = "Compare Hotel A and Hotel B and save the cheaper option"


def test_public_hotel_price_message_passes_data_flow_checks(build_label):
    verdict = evaluate_flow(
        [build_label()],
        tool="send_message",
        destination="bob.example",
        destination_class=DestinationClass.KNOWN_EXTERNAL,
        declared_purpose="share comparison result",
        purpose_context=HOTEL_OBJECTIVE,
    )
    assert verdict.decision is DecisionType.ALLOW
    assert verdict.matched_rules == []
    assert verdict.risk_score == 0.0


def test_critical_api_key_to_unknown_external_blocks(build_api_key_label):
    verdict = evaluate_flow(
        [build_api_key_label()],
        tool="send_message",
        destination="attacker.example",
        destination_class=DestinationClass.UNKNOWN_EXTERNAL,
        declared_purpose="share comparison result",
        purpose_context=HOTEL_OBJECTIVE,
    )
    assert verdict.decision is DecisionType.BLOCK
    assert verdict.rule_strength is RuleStrength.HARD_BLOCK
    assert verdict.risk_score == 1.0
    assert "SENSITIVE_DATA_TO_UNKNOWN_EXTERNAL" in verdict.matched_rules
    assert "DATA_DESTINATION_NOT_ALLOWED" in verdict.matched_rules
    assert "DATA_PURPOSE_MISMATCH" in verdict.matched_rules


def test_blocked_destination_class_blocks_any_controlled_data(build_label):
    verdict = evaluate_flow(
        [build_label()],
        tool="http_request",
        destination="attacker.example",
        destination_class=DestinationClass.BLOCKED,
    )
    assert verdict.decision is DecisionType.BLOCK
    assert "DESTINATION_BLOCKED" in verdict.matched_rules


def test_sensitive_data_cannot_leave_its_allowed_destinations(build_api_key_label):
    verdict = evaluate_flow(
        [build_api_key_label()],
        tool="http_request",
        destination="https://metrics.example:8443/ingest",
        destination_class=DestinationClass.KNOWN_EXTERNAL,
        declared_purpose="authentication",
        purpose_context="authentication service sync",
    )
    assert verdict.decision is DecisionType.BLOCK
    assert "DATA_DESTINATION_NOT_ALLOWED" in verdict.matched_rules


def test_critical_data_to_allowed_destination_with_matching_purpose_passes(build_api_key_label):
    verdict = evaluate_flow(
        [build_api_key_label()],
        tool="http_request",
        destination="internal-auth.example",
        destination_class=DestinationClass.TRUSTED,
        declared_purpose="authentication for internal auth service",
        purpose_context="service login flow",
    )
    assert verdict.decision is DecisionType.ALLOW


def test_confidential_purpose_mismatch_requires_approval(build_label):
    personal = build_label(
        data_id="data-personal-001",
        data_type="PERSONAL_DATA",
        sensitivity=Sensitivity.CONFIDENTIAL,
        purpose="medical_history",
    )
    verdict = evaluate_flow(
        [personal],
        tool="send_message",
        destination="bob.example",
        declared_purpose="share hotel comparison",
        purpose_context=HOTEL_OBJECTIVE,
    )
    assert verdict.decision is DecisionType.REQUIRE_APPROVAL
    assert verdict.rule_strength is RuleStrength.REQUIRE_APPROVAL
    assert "DATA_PURPOSE_MISMATCH" in verdict.matched_rules


def test_critical_purpose_mismatch_blocks(build_api_key_label):
    verdict = evaluate_flow(
        [build_api_key_label(allowed_destinations=[])],
        tool="write_file",
        declared_purpose="save cheaper hotel option",
        purpose_context=HOTEL_OBJECTIVE,
    )
    assert verdict.decision is DecisionType.BLOCK
    assert "DATA_PURPOSE_MISMATCH" in verdict.matched_rules


def test_sensitive_flow_without_purpose_context_fails_closed(build_api_key_label):
    verdict = evaluate_flow(
        [build_api_key_label(allowed_destinations=[])],
        tool="send_message",
        destination="bob.example",
    )
    assert verdict.decision is DecisionType.REQUIRE_APPROVAL
    assert "DATA_PURPOSE_UNRESOLVED" in verdict.matched_rules


def test_public_data_skips_purpose_binding_check(build_label):
    verdict = evaluate_flow(
        [build_label()],
        tool="send_message",
        destination="bob.example",
        declared_purpose=None,
        purpose_context=None,
    )
    assert verdict.decision is DecisionType.ALLOW


def test_empty_data_refs_allow_at_data_flow_layer():
    verdict = evaluate_flow([], tool="browse_web")
    assert verdict.decision is DecisionType.ALLOW


def test_worst_decision_wins_and_rules_merge(build_label, build_api_key_label):
    personal = build_label(
        data_id="data-personal-001",
        data_type="PERSONAL_DATA",
        sensitivity=Sensitivity.CONFIDENTIAL,
        purpose="medical_history",
        allowed_destinations=[],
    )
    verdict = evaluate_flow(
        [personal, build_api_key_label()],
        tool="http_request",
        destination="attacker.example",
        destination_class=DestinationClass.UNKNOWN_EXTERNAL,
        declared_purpose="share comparison",
        purpose_context=HOTEL_OBJECTIVE,
    )
    assert verdict.decision is DecisionType.BLOCK
    assert "SENSITIVE_DATA_TO_UNKNOWN_EXTERNAL" in verdict.matched_rules
    assert "DATA_PURPOSE_MISMATCH" in verdict.matched_rules


def test_normalize_destination_extracts_host_from_url_forms():
    assert normalize_destination("https://attacker.example/upload") == "attacker.example"
    assert normalize_destination("HTTP://Attacker.Example:8443/x?y=1") == "attacker.example"
    assert normalize_destination("user@internal-auth.example") == "internal-auth.example"
    assert normalize_destination("internal-auth.example") == "internal-auth.example"
