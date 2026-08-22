"""DataLabel registry, controlled propagation, and data-flow constraints."""

from .constraints import FlowVerdict, evaluate_flow, normalize_destination
from .propagation import (
    ConflictingDestinationConstraintsError,
    EmptySourceError,
    PropagationError,
    SensitivityDowngradeError,
    TransformationType,
    UncontrolledTransformationError,
    encode_data,
    extract_value,
    propagate,
)
from .registry import DataLabelRegistry, DuplicateDataLabelError, UnknownDataRefError

__all__ = [
    "ConflictingDestinationConstraintsError",
    "DataLabelRegistry",
    "DuplicateDataLabelError",
    "EmptySourceError",
    "FlowVerdict",
    "PropagationError",
    "SensitivityDowngradeError",
    "TransformationType",
    "UnknownDataRefError",
    "UncontrolledTransformationError",
    "encode_data",
    "evaluate_flow",
    "extract_value",
    "normalize_destination",
    "propagate",
]
