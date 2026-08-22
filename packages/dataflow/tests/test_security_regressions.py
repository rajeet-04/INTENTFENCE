import pytest
from intentfence_contracts import DecisionType, DestinationClass

from intentfence_dataflow import PropagationError, encode_data, evaluate_flow


def test_explicit_empty_destination_override_tightens_sensitive_label(build_api_key_label):
    secret = build_api_key_label()
    derived = encode_data(
        secret,
        data_id="data-no-egress-001",
        data_type="API_KEY",
        allowed_destinations=[],
    )
    assert derived.allowed_destinations == []


def test_sensitive_data_type_cannot_be_laundered_during_transform(build_api_key_label):
    secret = build_api_key_label()
    with pytest.raises(PropagationError):
        encode_data(
            secret,
            data_id="data-laundered-type-001",
            data_type="PUBLIC_DATA",
        )


def test_sensitive_http_request_without_destination_requires_approval(build_api_key_label):
    verdict = evaluate_flow(
        [build_api_key_label()],
        tool="http_request",
        destination=None,
        destination_class=DestinationClass.KNOWN_EXTERNAL,
        declared_purpose="authentication",
        purpose_context="authentication service sync",
    )
    assert verdict.decision is DecisionType.REQUIRE_APPROVAL
    assert "SENSITIVE_EGRESS_DESTINATION_MISSING" in verdict.matched_rules


def test_blocked_destination_class_blocks_without_destination_string(build_label):
    verdict = evaluate_flow(
        [build_label()],
        tool="http_request",
        destination=None,
        destination_class=DestinationClass.BLOCKED,
    )
    assert verdict.decision is DecisionType.BLOCK
    assert "DESTINATION_BLOCKED" in verdict.matched_rules


def test_unknown_external_without_destination_still_blocks_sensitive_data(build_api_key_label):
    verdict = evaluate_flow(
        [build_api_key_label()],
        tool="http_request",
        destination=None,
        destination_class=DestinationClass.UNKNOWN_EXTERNAL,
        declared_purpose="authentication",
        purpose_context="authentication service sync",
    )
    assert verdict.decision is DecisionType.BLOCK
    assert "SENSITIVE_DATA_TO_UNKNOWN_EXTERNAL" in verdict.matched_rules
