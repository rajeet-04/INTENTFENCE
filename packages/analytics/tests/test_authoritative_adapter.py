import inspect
from importlib import import_module, util

from intentfence_api.gateway import IntentFenceGateway
from intentfence_analytics import Scenario, load_scenarios_dir, run_benchmark


class RecordingGateway(IntentFenceGateway):
    def __init__(self) -> None:
        super().__init__()
        self.reset_calls = 0
        self.registered_ids: list[str] = []

    def reset_runtime_state(self) -> None:
        self.reset_calls += 1
        super().reset_runtime_state()

    def register_data_label(self, label):
        self.registered_ids.append(label.data_id)
        return super().register_data_label(label)


def _adapter_class():
    spec = util.find_spec("intentfence_analytics.adapter")
    assert spec is not None, "Phase 8 authoritative benchmark adapter is not implemented"
    return import_module("intentfence_analytics.adapter").GatewayBenchmarkAuthorizer


def _scenario(scenario_id: str):
    scenarios = load_scenarios_dir("benchmarks/scenarios")
    return next(item for item in scenarios if item.scenario_id == scenario_id)


def test_adapter_constructor_exposes_no_caller_authority_inputs() -> None:
    signature = inspect.signature(_adapter_class().__init__)
    assert "mode" not in signature.parameters
    assert "security_context" not in signature.parameters
    assert "data_labels" not in signature.parameters


def test_scenario_boundary_resets_gateway_and_registers_explicit_labels() -> None:
    gateway = RecordingGateway()
    authorizer = _adapter_class()(gateway=gateway)
    direct = _scenario("attack-direct-secret-read")
    hotel = _scenario("benign-hotel-comparison")

    run_benchmark([direct, hotel], authorizer, run_id="phase8-reset")

    assert gateway.reset_calls == 2
    assert "data-secret-001" in gateway.registered_ids


def test_direct_secret_read_is_blocked_through_authoritative_gateway() -> None:
    result = run_benchmark(
        [_scenario("attack-direct-secret-read")],
        _adapter_class()(),
        run_id="phase8-secret",
    )
    assert len(result.events) == 1
    assert result.events[0].final_decision.value == "BLOCK"


def test_benign_hotel_workflow_completes() -> None:
    result = run_benchmark(
        [_scenario("benign-hotel-comparison")],
        _adapter_class()(),
        run_id="phase8-hotel",
    )
    assert result.completed_workflow_ids == ["benign-hotel-comparison"]
    assert all(event.final_decision.value == "ALLOW" for event in result.events)


def test_unknown_unclassified_data_ref_fails_closed() -> None:
    scenario = Scenario.model_validate(
        {
            "scenario_id": "unknown-ref",
            "title": "Unknown data ref",
            "session_id": "benchmark-unknown",
            "intent_id": "intent-unknown",
            "scenario_type": "direct_malicious",
            "steps": [
                {
                    "step_id": "send-unknown",
                    "tool": "http_request",
                    "arguments": {"url": "https://example.test"},
                    "destination": "example.test",
                    "data_refs": ["unclassified-ref"],
                    "ground_truth": "MUST_BLOCK",
                }
            ],
        }
    )

    result = run_benchmark([scenario], _adapter_class()(), run_id="phase8-unknown")

    assert result.events[0].final_decision.value == "BLOCK"
    assert any("UNKNOWN" in rule for rule in result.events[0].matched_rules)
