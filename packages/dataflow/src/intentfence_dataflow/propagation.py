from collections.abc import Sequence
from datetime import UTC, datetime
from enum import StrEnum

from intentfence_contracts import DataLabel, ResourceClass, Sensitivity
from pydantic import AwareDatetime

SENSITIVITY_RANK: dict[Sensitivity, int] = {
    Sensitivity.PUBLIC: 0,
    Sensitivity.INTERNAL: 1,
    Sensitivity.CONFIDENTIAL: 2,
    Sensitivity.CRITICAL: 3,
}


class PropagationError(Exception):
    pass


class EmptySourceError(PropagationError):
    def __init__(self, operation: str) -> None:
        self.operation = operation
        super().__init__(
            f"Controlled transformation requires at least one source label: {operation}"
        )


class UncontrolledTransformationError(PropagationError):
    def __init__(self, operation: str) -> None:
        self.operation = operation
        super().__init__(f"Uncontrolled transformation cannot propagate labels: {operation}")


class SensitivityDowngradeError(PropagationError):
    def __init__(self, computed: Sensitivity, requested: Sensitivity) -> None:
        self.computed = computed
        self.requested = requested
        super().__init__(
            f"Sensitivity cannot be downgraded from {computed.value} to {requested.value}"
        )


class ConflictingDestinationConstraintsError(PropagationError):
    def __init__(self) -> None:
        super().__init__(
            "Destination constraints conflict; derived data would have no permitted destination"
        )


class TransformationType(StrEnum):
    EXTRACT_VALUE = "extract_value"
    ENCODE_DATA = "encode_data"


def _coerce_operation(operation: TransformationType | str) -> TransformationType:
    try:
        return TransformationType(operation)
    except ValueError:
        raise UncontrolledTransformationError(str(operation)) from None


def _dedupe(items: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def _intersect_allowed_destinations(
    sources: Sequence[DataLabel], override: list[str] | None
) -> list[str]:
    restricted = [source.allowed_destinations for source in sources if source.allowed_destinations]
    if override:
        restricted.append(override)
    if not restricted:
        return []
    intersection = set(restricted[0])
    for other in restricted[1:]:
        intersection &= set(other)
    if not intersection:
        raise ConflictingDestinationConstraintsError()
    return [dest for dest in restricted[0] if dest in intersection]


def propagate(
    sources: Sequence[DataLabel],
    *,
    operation: TransformationType | str,
    data_id: str,
    data_type: str,
    created_at: AwareDatetime | None = None,
    sensitivity: Sensitivity | None = None,
    provenance: str | None = None,
    purpose: str | None = None,
    owner: str | None = None,
    source: str | None = None,
    source_class: ResourceClass | None = None,
    allowed_destinations: list[str] | None = None,
) -> DataLabel:
    coerced_operation = _coerce_operation(operation)
    if not sources:
        raise EmptySourceError(coerced_operation.value)
    highest = max(sources, key=lambda label: SENSITIVITY_RANK[label.sensitivity])
    computed_sensitivity = highest.sensitivity
    if (
        sensitivity is not None
        and SENSITIVITY_RANK[sensitivity] < SENSITIVITY_RANK[computed_sensitivity]
    ):
        raise SensitivityDowngradeError(computed_sensitivity, sensitivity)
    final_sensitivity = sensitivity if sensitivity is not None else computed_sensitivity
    lineage = _dedupe([ref for parent in sources for ref in (parent.data_id, *parent.derived_from)])
    return DataLabel(
        data_id=data_id,
        data_type=data_type,
        source=source if source is not None else highest.source,
        source_class=source_class if source_class is not None else highest.source_class,
        provenance=provenance if provenance is not None else highest.provenance,
        sensitivity=final_sensitivity,
        purpose=purpose if purpose is not None else sources[0].purpose,
        owner=owner if owner is not None else highest.owner,
        allowed_destinations=_intersect_allowed_destinations(sources, allowed_destinations),
        derived_from=lineage,
        created_at=created_at if created_at is not None else datetime.now(UTC),
    )


def extract_value(
    parent: DataLabel,
    *,
    data_id: str,
    data_type: str,
    created_at: AwareDatetime | None = None,
    sensitivity: Sensitivity | None = None,
    provenance: str | None = None,
    purpose: str | None = None,
    owner: str | None = None,
    source: str | None = None,
    source_class: ResourceClass | None = None,
    allowed_destinations: list[str] | None = None,
) -> DataLabel:
    return propagate(
        [parent],
        operation=TransformationType.EXTRACT_VALUE,
        data_id=data_id,
        data_type=data_type,
        created_at=created_at,
        sensitivity=sensitivity,
        provenance=provenance,
        purpose=purpose,
        owner=owner,
        source=source,
        source_class=source_class,
        allowed_destinations=allowed_destinations,
    )


def encode_data(
    parent: DataLabel,
    *,
    data_id: str,
    data_type: str,
    created_at: AwareDatetime | None = None,
    sensitivity: Sensitivity | None = None,
    provenance: str | None = None,
    purpose: str | None = None,
    owner: str | None = None,
    source: str | None = None,
    source_class: ResourceClass | None = None,
    allowed_destinations: list[str] | None = None,
) -> DataLabel:
    return propagate(
        [parent],
        operation=TransformationType.ENCODE_DATA,
        data_id=data_id,
        data_type=data_type,
        created_at=created_at,
        sensitivity=sensitivity,
        provenance=provenance,
        purpose=purpose,
        owner=owner,
        source=source,
        source_class=source_class,
        allowed_destinations=allowed_destinations,
    )
