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

EGRESS_RESTRICTED_SENSITIVITIES = frozenset({Sensitivity.CONFIDENTIAL, Sensitivity.CRITICAL})
CREDENTIAL_DATA_TYPES = frozenset({"API_KEY", "PASSWORD"})

METADATA_OVERRIDE_FIELDS = ("provenance", "purpose", "owner", "source", "source_class")


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


class MetadataRewriteError(PropagationError):
    def __init__(self, fields: Sequence[str]) -> None:
        self.fields = list(fields)
        super().__init__(
            "Controlled transformations cannot rewrite security metadata: " + ", ".join(self.fields)
        )


class ConflictingPurposeError(PropagationError):
    def __init__(self, purposes: set[str]) -> None:
        self.purposes = sorted(purposes)
        super().__init__(
            "Sensitive source labels carry conflicting purposes and require explicit "
            f"authorized rebinding: {', '.join(self.purposes)}"
        )


class ProtectedDataTypeRewriteError(PropagationError):
    def __init__(self, source_types: set[str], requested: str) -> None:
        self.source_types = sorted(source_types)
        self.requested = requested
        super().__init__(
            "Credential data classification cannot be rewritten by a controlled transformation: "
            f"source={','.join(self.source_types)} requested={requested}"
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
    restricted: list[set[str]] = []
    for source in sources:
        if not source.allowed_destinations:
            if source.sensitivity in EGRESS_RESTRICTED_SENSITIVITIES:
                return []
            continue
        restricted.append(set(source.allowed_destinations))
    if override is not None:
        if not override:
            return []
        restricted.append(set(override))
    if not restricted:
        return []
    intersection = set(restricted[0])
    for other in restricted[1:]:
        intersection &= other
    if not intersection:
        raise ConflictingDestinationConstraintsError()
    return [dest for dest in sorted(intersection)]


def _reject_metadata_overrides(
    provenance: str | None,
    purpose: str | None,
    owner: str | None,
    source: str | None,
    source_class: ResourceClass | None,
) -> None:
    attempted = {
        "provenance": provenance,
        "purpose": purpose,
        "owner": owner,
        "source": source,
        "source_class": source_class,
    }
    rewritten = sorted(field for field, value in attempted.items() if value is not None)
    if rewritten:
        raise MetadataRewriteError(rewritten)


def _resolve_derived_purpose(sources: Sequence[DataLabel]) -> str:
    sensitive_sources = [
        label for label in sources if label.sensitivity in EGRESS_RESTRICTED_SENSITIVITIES
    ]
    if not sensitive_sources:
        return sources[0].purpose
    purposes = {label.purpose for label in sensitive_sources}
    if len(purposes) > 1:
        raise ConflictingPurposeError(purposes)
    return next(iter(purposes))


def _resolve_derived_data_type(sources: Sequence[DataLabel], requested: str) -> str:
    credential_types = {
        label.data_type.strip().upper()
        for label in sources
        if label.data_type.strip().upper() in CREDENTIAL_DATA_TYPES
    }
    if not credential_types:
        return requested
    requested_type = requested.strip().upper()
    if len(credential_types) != 1 or requested_type not in credential_types:
        raise ProtectedDataTypeRewriteError(credential_types, requested_type)
    return requested_type


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
    _reject_metadata_overrides(provenance, purpose, owner, source, source_class)
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
        data_type=_resolve_derived_data_type(sources, data_type),
        source=highest.source,
        source_class=highest.source_class,
        provenance=highest.provenance,
        sensitivity=final_sensitivity,
        purpose=_resolve_derived_purpose(sources),
        owner=highest.owner,
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
