from datetime import UTC, datetime

import pytest
from intentfence_contracts import DataLabel, ResourceClass, Sensitivity


def _build_label(**overrides) -> DataLabel:
    payload: dict = {
        "data_id": "data-hotel-price-001",
        "data_type": "PUBLIC_DATA",
        "source": "hotel-a.example",
        "source_class": ResourceClass.PUBLIC_WEB,
        "provenance": "EXTERNAL_WEB",
        "sensitivity": Sensitivity.PUBLIC,
        "purpose": "hotel_comparison",
        "owner": "user",
        "allowed_destinations": [],
        "derived_from": [],
        "created_at": datetime(2026, 8, 22, 9, 0, tzinfo=UTC),
    }
    payload.update(overrides)
    return DataLabel.model_validate(payload)


def _build_api_key_label(**overrides) -> DataLabel:
    payload: dict = {
        "data_id": "data-secret-001",
        "data_type": "API_KEY",
        "source": ".env",
        "source_class": ResourceClass.PRIVATE_FILE,
        "provenance": "USER_OWNED",
        "sensitivity": Sensitivity.CRITICAL,
        "purpose": "authentication",
        "owner": "user",
        "allowed_destinations": ["internal-auth.example"],
        "derived_from": [],
        "created_at": datetime(2026, 8, 22, 9, 0, tzinfo=UTC),
    }
    payload.update(overrides)
    return DataLabel.model_validate(payload)


@pytest.fixture
def build_label():
    return _build_label


@pytest.fixture
def build_api_key_label():
    return _build_api_key_label
