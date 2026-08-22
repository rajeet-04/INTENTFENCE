from collections.abc import Sequence

from intentfence_contracts import DataLabel
from intentfence_dataflow import DataLabelRegistry


class TrustedDataRegistry:
    """Gateway-owned wrapper around the canonical Phase 4 label registry."""

    def __init__(self) -> None:
        self._registry = DataLabelRegistry()

    def register(self, label: DataLabel) -> DataLabel:
        return self._registry.register(label)

    def resolve_known(self, data_refs: Sequence[str]) -> list[DataLabel]:
        labels: list[DataLabel] = []
        for data_ref in data_refs:
            label = self._registry.get(data_ref)
            if label is not None:
                labels.append(label)
        return labels

    def reset(self) -> None:
        self._registry = DataLabelRegistry()
