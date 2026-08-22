from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

from intentfence_contracts import (
    DecisionSource,
    DecisionType,
    RuleStrength,
)
from pydantic import BaseModel, ConfigDict, Field

from .events import BenchmarkEvent
from .scenarios import GroundTruth, Scenario, ScenarioStep, ScenarioType


class AuthorizationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: DecisionType
    decision_source: DecisionSource | None = None
    risk_score: float | None = Field(default=None, ge=0.0, le=1.0)
    matched_rules: list[str] = Field(default_factory=list)
    rule_strength: RuleStrength | None = None
    semantic_relevance_score: float | None = Field(default=None, ge=0.0, le=1.0)
    semantic_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    intent_drift_score: float | None = Field(default=None, ge=0.0, le=1.0)
    accumulated_risk: float | None = Field(default=None, ge=0.0, le=1.0)
    chain_involved: bool = False
    latency_ms: int = Field(default=0, ge=0)
    model_used: str | None = None


Authorizer = Callable[[ScenarioStep, Scenario], AuthorizationResult]


class RunResult(BaseModel):
    run_id: str
    events: list[BenchmarkEvent]
    completed_workflow_ids: list[str] = Field(default_factory=list)


def ground_truth_satisfied(decision: DecisionType, ground_truth: GroundTruth) -> bool:
    if ground_truth is GroundTruth.MUST_BLOCK:
        return decision is DecisionType.BLOCK
    return decision is not DecisionType.BLOCK


def run_benchmark(
    scenarios: list[Scenario],
    authorizer: Authorizer,
    *,
    run_id: str | None = None,
    now: Callable[[], datetime] | None = None,
) -> RunResult:
    resolved_run_id = run_id if run_id is not None else uuid4().hex
    now_factory = now if now is not None else (lambda: datetime.now(UTC))
    events: list[BenchmarkEvent] = []
    completed_workflow_ids: list[str] = []
    for scenario in scenarios:
        blocked_steps = 0
        for step in scenario.steps:
            result = authorizer(step, scenario)
            events.append(
                BenchmarkEvent(
                    run_id=resolved_run_id,
                    created_at=now_factory(),
                    scenario_id=scenario.scenario_id,
                    scenario_type=scenario.scenario_type,
                    attack_type=scenario.attack_type,
                    mutation_type=scenario.mutation_type,
                    ground_truth=step.ground_truth,
                    step_id=step.step_id,
                    session_id=scenario.session_id,
                    intent_id=scenario.intent_id,
                    tool=step.tool,
                    resource_class=step.resource_class,
                    destination=step.destination,
                    destination_class=step.destination_class,
                    data_refs=list(step.data_refs),
                    data_sensitivity=step.data_sensitivity,
                    matched_rules=list(result.matched_rules),
                    rule_strength=result.rule_strength,
                    semantic_relevance_score=result.semantic_relevance_score,
                    semantic_confidence=result.semantic_confidence,
                    intent_drift_score=result.intent_drift_score,
                    accumulated_risk=result.accumulated_risk,
                    risk_score=result.risk_score,
                    chain_involved=result.chain_involved,
                    decision_source=result.decision_source,
                    final_decision=result.decision,
                    latency_ms=result.latency_ms,
                    model_used=result.model_used,
                )
            )
            if result.decision is DecisionType.BLOCK:
                blocked_steps += 1
        benign_completed = scenario.scenario_type is ScenarioType.BENIGN and blocked_steps == 0
        if benign_completed:
            completed_workflow_ids.append(scenario.scenario_id)
    return RunResult(
        run_id=resolved_run_id,
        events=events,
        completed_workflow_ids=completed_workflow_ids,
    )
