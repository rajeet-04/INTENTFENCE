"""Deterministic classification primitives for IntentFence."""

from .authority import (
    AuthorityLevel,
    classify_authority,
    find_authority_claim,
    join_argument_values,
)
from .authority import (
    find_authority_claim_in_arguments as find_argument_authority_claim,
)
from .authority import has_authority_granting_power as source_grants_authority
from .config import ClassifierConfig
from .destinations import classify_destination, normalize_destination
from .extraction import extract_destination_argument, extract_resource_argument
from .resources import classify_resource, is_path_under_root, normalize_path

__all__ = [
    "AuthorityLevel",
    "ClassifierConfig",
    "classify_authority",
    "classify_destination",
    "classify_resource",
    "extract_destination_argument",
    "extract_resource_argument",
    "find_authority_claim",
    "find_argument_authority_claim",
    "is_path_under_root",
    "join_argument_values",
    "normalize_destination",
    "normalize_path",
    "source_grants_authority",
]
