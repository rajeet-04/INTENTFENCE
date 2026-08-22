import json
from enum import StrEnum
from pathlib import Path
from typing import Any

from intentfence_contracts import DestinationClass, ResourceClass, Sensitivity
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ScenarioValidationError(Exception):
    pass


class GroundTruth(StrEnum):
    MUST_BLOCK = "MUST_BLOCK"
    MUST_ALLOW = "MUST_ALLOW"


class ScenarioType(StrEnum):
    BENIGN = "benign"
    DIRECT_MALICIOUS = "direct_malicious"
    INDIRECT_INJECTION = "indirect_prompt_injection"
    MULTI_STEP_EXFILTRATION = "multi_step_exfiltration"
    DESTINATION_SUBSTITUTION = "destination_substitution"
    ENCODED_PAYLOAD = "encoded_payload"
    MUTATED_VARIANT = "mutated_variant"


class MutationType(StrEnum):
    NONE = "none"
    ENCODED_INSTRUCTIONS = "encoded_instructions"
    INDIRECT_PHRASING = "indirect_phrasing"
    DISGUISED_INSTRUCTIONS = "disguised_instructions"
    SPLIT_INSTRUCTIONS = "split_instructions"
    HIDDEN_INSTRUCTIONS = "hidden_instructions"
    MULTI_STEP_CHAIN = "multi_step_chain"
    TRANSFORMED_PAYLOAD = "transformed_payload"
    DESTINATION_SUBSTITUTION = "destination_substitution"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ScenarioStep(_Model):
    step_id: str = Field(min_length=1)
    tool: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)
    data_refs: list[str] = Field(default_factory=list)
    resource_class: ResourceClass | None = None
    destination: str | None = None
    destination_class: DestinationClass | None = None
    data_sensitivity: Sensitivity | None = None
    ground_truth: GroundTruth | None = None


class Scenario(_Model):
    scenario_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = ""
    session_id: str = Field(min_length=1)
    intent_id: str = Field(min_length=1)
    scenario_type: ScenarioType
    attack_type: str | None = None
    mutation_type: MutationType = MutationType.NONE
    steps: list[ScenarioStep] = Field(min_length=1)

    @property
    def is_malicious(self) -> bool:
        return self.scenario_type is not ScenarioType.BENIGN

    @property
    def has_ground_truth(self) -> bool:
        return all(step.ground_truth is not None for step in self.steps)


def load_scenario_file(path: Path) -> Scenario:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return Scenario.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        raise ScenarioValidationError(f"{path.name}: {error}") from error


def load_scenarios_dir(directory: Path | str) -> list[Scenario]:
    resolved = Path(directory)
    files = sorted(resolved.glob("*.json"))
    if not files:
        raise ScenarioValidationError(f"No scenario files found in {resolved}")
    scenarios: list[Scenario] = []
    seen_ids: set[str] = set()
    for path in files:
        scenario = load_scenario_file(path)
        if scenario.scenario_id in seen_ids:
            raise ScenarioValidationError(
                f"{path.name}: duplicate scenario_id {scenario.scenario_id}"
            )
        seen_ids.add(scenario.scenario_id)
        scenarios.append(scenario)
    return scenarios


def scenarios_missing_ground_truth(scenarios: list[Scenario]) -> list[str]:
    return [scenario.scenario_id for scenario in scenarios if not scenario.has_ground_truth]
