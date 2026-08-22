from datetime import UTC, datetime

import pytest
from intentfence_contracts import ResourceClass, Sensitivity

from intentfence_dataflow import (
    ConflictingDestinationConstraintsError,
    ConflictingPurposeError,
    EmptySourceError,
    MetadataRewriteError,
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


def test_sensitive_parent_with_empty_destinations_denies_egress_in_derived_data(
    build_api_key_label,
):
    locked = build_api_key_label(data_id="data-locked-001", allowed_destinations=[])
    scoped = build_api_key_label(
        data_id="data-secret-002",
        allowed_destinations=["internal-auth.example"],
    )
    combined = propagate(
        [locked, scoped],
        operation="encode_data",
        data_id="data-combined-001",
        data_type="API_KEY",
        created_at=LATER,
    )
    assert combined.sensitivity is Sensitivity.CRITICAL
    assert combined.allowed_destinations == []


def test_confidential_parent_with_empty_destinations_also_denies_egress(
    build_api_key_label,
):
    restricted = build_api_key_label(
        data_id="data-report-001",
        data_type="REPORT",
        sensitivity=Sensitivity.CONFIDENTIAL,
        allowed_destinations=[],
    )
    scoped = build_api_key_label()
    combined = propagate(
        [restricted, scoped],
        operation="extract_value",
        data_id="data-combined-002",
        data_type="MIXED",
        created_at=LATER,
    )
    assert combined.allowed_destinations == []


def test_low_sensitivity_empty_destinations_stay_unconstrained_in_combination(
    build_label,
    build_api_key_label,
):
    price = build_label()
    secret = build_api_key_label()
    combined = propagate(
        [price, secret],
        operation="encode_data",
        data_id="data-combined-003",
        data_type="MIXED",
        created_at=LATER,
    )
    assert combined.allowed_destinations == ["internal-auth.example"]


@pytest.mark.parametrize(
    ("override_field", "override_value"),
    [
        ("provenance", "EXTERNAL_WEB"),
        ("purpose", "hotel_comparison"),
        ("owner", "attacker"),
        ("source", "hotel-a.example"),
        ("source_class", ResourceClass.PUBLIC_WEB),
    ],
)
@pytest.mark.parametrize("transform", [extract_value, encode_data])
def test_transformations_cannot_rewrite_security_metadata(
    transform, override_field, override_value, build_api_key_label
):
    secret = build_api_key_label()
    with pytest.raises(MetadataRewriteError):
        transform(
            secret,
            data_id="data-laundered-001",
            data_type="API_KEY",
            created_at=LATER,
            **{override_field: override_value},
        )


def test_propagate_cannot_rewrite_security_metadata(build_api_key_label):
    secret = build_api_key_label()
    with pytest.raises(MetadataRewriteError) as error:
        propagate(
            [secret],
            operation="encode_data",
            data_id="data-laundered-002",
            data_type="API_KEY",
            created_at=LATER,
            purpose="hotel_comparison",
            provenance="EXTERNAL_WEB",
        )
    assert set(error.value.fields) == {"purpose", "provenance"}


def test_conflicting_sensitive_purposes_fail_closed(build_api_key_label):
    auth = build_api_key_label()
    analytics = build_api_key_label(
        data_id="data-analytics-001",
        purpose="market_analytics",
    )
    with pytest.raises(ConflictingPurposeError):
        propagate(
            [auth, analytics],
            operation="encode_data",
            data_id="data-conflicted-001",
            data_type="MIXED",
            created_at=LATER,
        )


def test_sensitive_purpose_wins_over_low_sensitivity_conflict(
    build_label,
    build_api_key_label,
):
    price = build_label(purpose="hotel_comparison")
    secret = build_api_key_label(purpose="authentication")
    combined = propagate(
        [price, secret],
        operation="encode_data",
        data_id="data-mixed-purpose-001",
        data_type="MIXED",
        created_at=LATER,
    )
    assert combined.purpose == "authentication"


def test_low_sensitivity_only_purpose_conflict_keeps_first_source(build_label):
    first = build_label(purpose="hotel_comparison")
    second = build_label(data_id="data-price-b-002", purpose="weather_check")
    combined = propagate(
        [first, second],
        operation="extract_value",
        data_id="data-lowconflict-001",
        data_type="PUBLIC_DATA",
        created_at=LATER,
    )
    assert combined.purpose == "hotel_comparison"
