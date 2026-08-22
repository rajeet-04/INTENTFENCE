from intentfence_contracts import DecisionType
from policy_testkit import WORKSPACE_CONFIG, make_contract, make_policy_input, make_request

from intentfence_policy import evaluate_policy


def test_allowed_secret_basename_does_not_authorize_different_path():
    contract = make_contract(
        allowed_tools=["read_file"],
        allowed_resources=["api_key.txt"],
        forbidden_resources=[],
        approval_required_actions=[],
    )
    request = make_request(
        tool="read_file",
        arguments={"path": "other/api_key.txt"},
    )
    policy_input, _ = make_policy_input(request=request, contract=contract)

    result = evaluate_policy(policy_input, config=WORKSPACE_CONFIG)

    assert result.decision is DecisionType.BLOCK
    assert "SECRET_ACCESS_UNRELATED_TO_INTENT" in result.matched_rules


def test_exact_allowed_secret_path_remains_authorized():
    contract = make_contract(
        allowed_tools=["read_file"],
        allowed_resources=["api_key.txt"],
        forbidden_resources=[],
        approval_required_actions=[],
    )
    request = make_request(
        tool="read_file",
        arguments={"path": "api_key.txt"},
    )
    policy_input, _ = make_policy_input(request=request, contract=contract)

    result = evaluate_policy(policy_input, config=WORKSPACE_CONFIG)

    assert result.decision is DecisionType.ALLOW
