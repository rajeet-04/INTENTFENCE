from collections.abc import Sequence
from typing import Protocol

from intentfence_contracts import DataLabel, IntentContract, ResourceClass, SecurityContext, ToolRequest

from .models import ComponentDecision


class PolicyAdapter(Protocol):
    def evaluate(
        self,
        request: ToolRequest,
        intent_contract: IntentContract,
        security_context: SecurityContext,
        *,
        resource_class: ResourceClass,
        destination: str | None,
        data_labels: Sequence[DataLabel] = (),
    ) -> ComponentDecision: ...


class StateDataFlowAdapter(Protocol):
    def evaluate(
        self,
        request: ToolRequest,
        intent_contract: IntentContract,
        security_context: SecurityContext,
        *,
        resource_class: ResourceClass,
        destination: str | None,
        data_labels: Sequence[DataLabel] = (),
    ) -> ComponentDecision: ...


class SemanticAdapter(Protocol):
    def evaluate(
        self,
        request: ToolRequest,
        intent_contract: IntentContract,
        security_context: SecurityContext,
        *,
        resource_class: ResourceClass,
        destination: str | None,
        data_labels: Sequence[DataLabel] = (),
    ) -> ComponentDecision: ...
