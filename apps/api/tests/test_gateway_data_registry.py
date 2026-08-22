from datetime import UTC, datetime

import pytest
from intentfence_contracts import DataLabel, ResourceClass, Sensitivity
from intentfence_dataflow import DuplicateDataLabelError

from intentfence_api.gateway.data_registry import TrustedDataRegistry

NOW = datetime(2026, 8, 22, tzinfo=UTC)


def _label(data_id: str) -> DataLabel:
    return DataLabel(
        data_id=data_id,
        data_type="PUBLIC_DATA",
        source="trusted-test-source",
        source_class=ResourceClass.PUBLIC_WEB,
        provenance="USER_OWNED",
        sensitivity=Sensitivity.PUBLIC,
        purpose="hotel comparison",
        owner="user",
        allowed_destinations=[],
        derived_from=[],
        created_at=NOW,
    )


def test_trusted_registry_resolves_only_gateway_registered_labels() -> None:
    registry = TrustedDataRegistry()
    label = registry.register(_label("known-ref"))

    assert registry.resolve_known(["known-ref", "missing-ref"]) == [label]


def test_trusted_registry_preserves_canonical_duplicate_rejection() -> None:
    registry = TrustedDataRegistry()
    registry.register(_label("duplicate-ref"))

    with pytest.raises(DuplicateDataLabelError):
        registry.register(_label("duplicate-ref"))
