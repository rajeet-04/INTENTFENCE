from datetime import UTC, datetime

from intentfence_contracts import (
    DataLabel,
    DecisionType,
    IntentContract,
    ResourceClass,
    RiskTolerance,
    Sensitivity,
    SourceContext,
)
from intentfence_dataflow import encode_data

from intentfence_api.gateway.service import IntentFenceGateway
from intentfence_api.gateway.tools import normalize_tool_request

NOW = datetime(2026, 8, 22, tzinfo=UTC)


class ExplodingSemanticAdapter:
    def evaluate(self, *args, **kwargs):
        raise AssertionError("semantic evaluation must not run after a Phase 4 hard block")


def _contract() -> IntentContract:
    return IntentContract(
        intent_id="phase4-integration-intent",
        session_id="phase4-integration-session",
        objective="Use authentication data only for approved authentication operations.",
        allowed_tools=["send_message"],
        allowed_resources=["approved_data"],
        allowed_destinations=["internal-auth.example", "bob.example"],
        risk_tolerance=RiskTolerance.MEDIUM,
        issued_at=NOW,
        contract_version=1,
    )


def _credential() -> DataLabel:
    return DataLabel(
        data_id="phase4-secret",
        data_type="API_KEY",
        source="credential-store",
        source_class=ResourceClass.CREDENTIAL,
        provenance="USER_OWNED",
        sensitivity=Sensitivity.CRITICAL,
        purpose="authentication",
        owner="user",
        allowed_destinations=["internal-auth.example"],
        created_at=NOW,
    )


def _public_price() -> DataLabel:
    return DataLabel(
        data_id="hotel-price",
        data_type="PUBLIC_DATA",
        source="hotel-a.example",
        source_class=ResourceClass.PUBLIC_WEB,
        provenance="EXTERNAL_WEB",
        sensitivity=Sensitivity.PUBLIC,
        purpose="hotel_comparison",
        owner="user",
        allowed_destinations=["bob.example"],
        created_at=NOW,
    )


def _message_request(*, request_id: str, destination: str, data_ref: str):
    return normalize_tool_request(
        request_id=request_id,
        session_id="phase4-integration-session",
        agent_id="agent-1",
        intent_id="phase4-integration-intent",
        tool="send_message",
        arguments={"recipient": destination, "content_ref": data_ref},
        data_refs=[data_ref],
        source_context=SourceContext.SYSTEM,
        timestamp=NOW,
    )


def test_phase4_transformed_credential_hard_block_survives_gateway_and_skips_semantic() -> None:
    derived = encode_data(
        _credential(),
        data_id="phase4-derived-secret",
        data_type="PUBLIC_DATA",
        created_at=NOW,
    )
    assert derived.data_type == "API_KEY"
    assert derived.sensitivity is Sensitivity.CRITICAL
    assert derived.derived_from == ["phase4-secret"]

    calls = []
    gateway = IntentFenceGateway(semantic_adapter=ExplodingSemanticAdapter())
    gateway.register_data_label(derived)
    result = gateway.intercept(
        _message_request(
            request_id="phase4-block",
            destination="internal-auth.example",
            data_ref=derived.data_id,
        ),
        _contract(),
        handler=lambda arguments: calls.append(arguments) or {"status": "sent"},
    )

    assert result.decision is DecisionType.BLOCK
    assert result.executed is False
    assert calls == []
    assert "CREDENTIAL_DATA_IN_MESSAGING" in result.receipt.matched_rules


def test_phase4_public_data_still_allows_safe_gateway_workflow() -> None:
    calls = []
    gateway = IntentFenceGateway()
    label = _public_price()
    gateway.register_data_label(label)
    result = gateway.intercept(
        _message_request(
            request_id="phase4-allow",
            destination="bob.example",
            data_ref=label.data_id,
        ),
        _contract(),
        handler=lambda arguments: calls.append(arguments) or {"status": "sent"},
    )

    assert result.decision is DecisionType.ALLOW
    assert result.executed is True
    assert len(calls) == 1
    assert "DATAFLOW_LABELS_ALLOW" in result.receipt.matched_rules
