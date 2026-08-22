"""Benchmark scenarios, event records, harness, and security KPIs."""

from .events import BenchmarkEvent, CompletionStatus, EventStore
from .kpis import DEFAULT_TARGETS, build_summary, driver_metrics, guardrails, headline_kpis
from .runner import (
    AuthorizationResult,
    Authorizer,
    RunResult,
    ground_truth_satisfied,
    run_benchmark,
)
from .scenarios import (
    GroundTruth,
    MutationType,
    Scenario,
    ScenarioStep,
    ScenarioType,
    ScenarioValidationError,
    load_scenario_file,
    load_scenarios_dir,
    scenarios_missing_ground_truth,
)

__all__ = [
    "AuthorizationResult",
    "Authorizer",
    "BenchmarkEvent",
    "CompletionStatus",
    "DEFAULT_TARGETS",
    "EventStore",
    "GroundTruth",
    "MutationType",
    "RunResult",
    "Scenario",
    "ScenarioStep",
    "ScenarioType",
    "ScenarioValidationError",
    "build_summary",
    "driver_metrics",
    "ground_truth_satisfied",
    "guardrails",
    "headline_kpis",
    "load_scenario_file",
    "load_scenarios_dir",
    "run_benchmark",
    "scenarios_missing_ground_truth",
]
