from datetime import UTC, datetime

import pytest
from intentfence_contracts import Sensitivity
from pydantic import ValidationError

from intentfence_dataflow import (
    DataLabelRegistry,
    DuplicateDataLabelError,
    UnknownDataRefError,
)

LATER = datetime(2026, 8, 22, 9, 5, tzinfo=UTC)


def test_register_and_get_roundtrip(build_api_key_label):
    registry = DataLabelRegistry()
    label = build_api_key_label()
    registry.register(label)
    assert registry.get("data-secret-001") == label
    assert "data-secret-001" in registry
    assert len(registry) == 1


def test_register_rejects_duplicate_data_id(build_api_key_label):
    registry = DataLabelRegistry()
    registry.register(build_api_key_label())
    with pytest.raises(DuplicateDataLabelError):
        registry.register(build_api_key_label())


def test_require_raises_for_unknown_ref():
    registry = DataLabelRegistry()
    with pytest.raises(UnknownDataRefError):
        registry.require("data-missing-999")


def test_resolve_preserves_request_order(build_label, build_api_key_label):
    registry = DataLabelRegistry()
    price = build_label(data_id="data-price-001")
    secret = build_api_key_label()
    registry.register(price)
    registry.register(secret)
    resolved = registry.resolve(["data-secret-001", "data-price-001"])
    assert [label.data_id for label in resolved] == ["data-secret-001", "data-price-001"]


def test_all_labels_returns_registered_metadata(build_label, build_api_key_label):
    registry = DataLabelRegistry()
    registry.register(build_label())
    registry.register(build_api_key_label())
    assert {label.data_id for label in registry.all_labels()} == {
        "data-hotel-price-001",
        "data-secret-001",
    }


def test_registry_stores_metadata_only_and_never_raw_values(build_api_key_label):
    with pytest.raises(ValidationError):
        build_api_key_label(raw_value="sk-live-abc123")
    registry = DataLabelRegistry()
    label = registry.register(build_api_key_label())
    stored = registry.require(label.data_id)
    assert stored.sensitivity is Sensitivity.CRITICAL
    assert not hasattr(stored, "value")
    assert not hasattr(stored, "raw_value")
    assert "sk-live" not in stored.model_dump_json()


def test_registry_accepts_labels_with_lineage_and_timestamps(build_api_key_label):
    registry = DataLabelRegistry()
    derived = build_api_key_label(
        data_id="data-derived-002",
        derived_from=["data-secret-001"],
        created_at=LATER,
    )
    registry.register(derived)
    assert registry.get("data-derived-002").derived_from == ["data-secret-001"]
