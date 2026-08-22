from datetime import UTC, datetime

import pytest
from intentfence_contracts import Sensitivity

from intentfence_dataflow import (
    ConflictingDestinationConstraintsError,
    EmptySourceError,
    SensitivityDowngradeError,
    UncontrolledTransformationError,
    encode_data,
    extract_value,
    propagate,
)

LATER = datetime(2026, 8, 22, 9, 5, tzinfo=UTC)


def test_extracted_hotel_price_stays_public_with_lineage(build_label):
    price = build_label()
    extracted = extract_value(
        price,
        data_id="data-price-extracted-001",
        data_type="PUBLIC_DATA",
        created_at=LATER,
    )
    assert extracted.sensitivity is Sensitivity.PUBLIC
    assert extracted.derived_from == ["data-hotel-price-001"]
    assert extracted.purpose == "hotel_comparison"
    assert extracted.provenance == "EXTERNAL_WEB"
    assert extracted.owner == "user"


def test_encoded_critical_secret_retains_sensitivity_lineage_and_destination(
    build_api_key_label,
):
    secret = build_api_key_label()
    encoded = encode_data(
        secret,
        data_id="data-derived-002",
        data_type="API_KEY",
        created_at=LATER,
    )
    assert encoded.sensitivity is Sensitivity.CRITICAL
    assert encoded.derived_from == ["data-secret-001"]
    assert encoded.allowed_destinations == ["internal-auth.example"]
    assert encoded.provenance == "USER_OWNED"
    assert encoded.source == ".env"


def test_transformation_chain_accumulates_full_origin_lineage(build_api_key_label):
    secret = build_api_key_label()
    extracted = extract_value(
        secret,
        data_id="data-extracted-001",
        data_type="API_KEY",
        created_at=LATER,
    )
    encoded = encode_data(
        extracted,
        data_id="data-derived-002",
        data_type="API_KEY",
        created_at=LATER,
    )
    assert encoded.sensitivity is Sensitivity.CRITICAL
    assert encoded.derived_from == ["data-extracted-001", "data-secret-001"]


def test_multi_source_propagation_takes_maximum_sensitivity(build_label, build_api_key_label):
    price = build_label()
    secret = build_api_key_label()
    combined = propagate(
        [price, secret],
        operation="encode_data",
        data_id="data-combined-001",
        data_type="MIXED",
        created_at=LATER,
    )
    assert combined.sensitivity is Sensitivity.CRITICAL
    assert set(combined.derived_from) == {"data-hotel-price-001", "data-secret-001"}


def test_propagation_never_downgrades_requested_sensitivity(build_api_key_label):
    secret = build_api_key_label()
    with pytest.raises(SensitivityDowngradeError):
        propagate(
            [secret],
            operation="encode_data",
            data_id="data-downgraded-001",
            data_type="API_KEY",
            sensitivity=Sensitivity.PUBLIC,
            created_at=LATER,
        )


def test_propagation_can_raise_sensitivity_explicitly(build_label):
    price = build_label()
    raised = propagate(
        [price],
        operation="extract_value",
        data_id="data-raised-001",
        data_type="PERSONAL_DATA",
        sensitivity=Sensitivity.CONFIDENTIAL,
        created_at=LATER,
    )
    assert raised.sensitivity is Sensitivity.CONFIDENTIAL


def test_destination_constraints_can_narrow_but_never_widen(build_api_key_label):
    secret = build_api_key_label()
    narrowed = encode_data(
        secret,
        data_id="data-narrowed-001",
        data_type="API_KEY",
        allowed_destinations=["internal-auth.example", "other.example"],
        created_at=LATER,
    )
    assert narrowed.allowed_destinations == ["internal-auth.example"]


def test_conflicting_destination_constraints_fail_closed(build_api_key_label):
    secret = build_api_key_label()
    with pytest.raises(ConflictingDestinationConstraintsError):
        encode_data(
            secret,
            data_id="data-widened-001",
            data_type="API_KEY",
            allowed_destinations=["anywhere.example"],
            created_at=LATER,
        )


def test_multi_source_destination_constraints_intersect(build_api_key_label):
    first = build_api_key_label(allowed_destinations=["a.example", "shared.example"])
    second = build_api_key_label(
        data_id="data-secret-002",
        allowed_destinations=["shared.example", "b.example"],
    )
    combined = propagate(
        [first, second],
        operation="encode_data",
        data_id="data-intersected-001",
        data_type="API_KEY",
        created_at=LATER,
    )
    assert combined.allowed_destinations == ["shared.example"]


def test_uncontrolled_operations_cannot_propagate_labels(build_label):
    price = build_label()
    with pytest.raises(UncontrolledTransformationError):
        propagate([price], operation="base64_encode", data_id="data-x-001", data_type="PUBLIC_DATA")


def test_propagation_requires_at_least_one_source():
    with pytest.raises(EmptySourceError):
        propagate([], operation="encode_data", data_id="data-empty-001", data_type="API_KEY")
