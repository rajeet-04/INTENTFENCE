import json
from dataclasses import dataclass

from intentfence_classification import (
    ClassifierConfig,
    classify_destination,
    classify_resource,
    extract_destination_argument,
    extract_destination_candidates,
    extract_resource_argument,
    normalize_destination,
)
from intentfence_contracts import (
    DataLabel,
    DecisionType,
    DestinationClass,
    IntentContract,
    ResourceClass,
    RuleStrength,
    SecurityContext,
    ToolRequest,
)
from intentfence_contracts.models import ContractModel
from pydantic import ConfigDict, Field


class PolicyInput(ContractModel):
    model_config = ConfigDict(extra="forbid")

    request: ToolRequest
    contract: IntentContract
    context: SecurityContext
    data_labels: dict[str, DataLabel] = Field(default_factory=dict)


class RuleOutcome(ContractModel):
    rule_id: str = Field(min_length=1)
    rule_strength: RuleStrength
    decision: DecisionType
    reason: str = Field(min_length=1)
    risk_contribution: float = Field(ge=0.0, le=1.0)


class PolicyResult(ContractModel):
    decision: DecisionType
    reason: str = Field(min_length=1)
    rule_id: str | None = None
    rule_strength: RuleStrength | None = None
    matched_rules: list[str] = Field(default_factory=list)
    risk_score: float = Field(ge=0.0, le=1.0)
    resource_class: ResourceClass | None = None
    destination: str | None = None
    destination_class: DestinationClass | None = None

    @property
    def requires_approval(self) -> bool:
        return self.decision == DecisionType.REQUIRE_APPROVAL


@dataclass(frozen=True, slots=True)
class EvaluationContext:
    input: PolicyInput
    config: ClassifierConfig
    resource_ref: str | None
    resource_class: ResourceClass | None
    destination: str | None
    destination_class: DestinationClass
    destination_candidates: tuple[str, ...]
    destination_hosts: tuple[str, ...]
    destination_ambiguous: bool
    argument_text: str

    @classmethod
    def build(
        cls,
        policy_input: PolicyInput,
        config: ClassifierConfig | None = None,
    ) -> "EvaluationContext":
        active_config = config or ClassifierConfig()
        arguments = policy_input.request.arguments
        resource_ref = extract_resource_argument(arguments)
        destination = extract_destination_argument(arguments)
        destination_candidates = extract_destination_candidates(arguments)
        destination_hosts = tuple(
            dict.fromkeys(
                host
                for candidate in destination_candidates
                if (host := normalize_destination(candidate))
            )
        )
        return cls(
            input=policy_input,
            config=active_config,
            resource_ref=resource_ref,
            resource_class=(
                classify_resource(resource_ref, active_config) if resource_ref else None
            ),
            destination=destination,
            destination_class=(
                classify_destination(
                    destination,
                    allowed_destinations=policy_input.contract.allowed_destinations,
                    blocked_destinations=active_config.blocked_destinations,
                    trusted_destinations=active_config.trusted_destinations,
                    known_external_domains=active_config.known_external_domains,
                )
                if destination
                else DestinationClass.UNKNOWN_EXTERNAL
            ),
            destination_candidates=destination_candidates,
            destination_hosts=destination_hosts,
            destination_ambiguous=len(destination_hosts) > 1,
            argument_text=json.dumps(arguments, sort_keys=True, default=str),
        )
