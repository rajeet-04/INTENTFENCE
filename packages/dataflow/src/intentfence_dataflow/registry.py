from intentfence_contracts import DataLabel


class DataFlowError(Exception):
    pass


class DuplicateDataLabelError(DataFlowError):
    def __init__(self, data_id: str) -> None:
        self.data_id = data_id
        super().__init__(f"Data label already registered: {data_id}")


class UnknownDataRefError(DataFlowError):
    def __init__(self, data_id: str) -> None:
        self.data_id = data_id
        super().__init__(f"Unknown data reference: {data_id}")


class DataLabelRegistry:
    def __init__(self) -> None:
        self._labels: dict[str, DataLabel] = {}

    def register(self, label: DataLabel) -> DataLabel:
        if label.data_id in self._labels:
            raise DuplicateDataLabelError(label.data_id)
        self._labels[label.data_id] = label
        return label

    def get(self, data_id: str) -> DataLabel | None:
        return self._labels.get(data_id)

    def require(self, data_id: str) -> DataLabel:
        label = self._labels.get(data_id)
        if label is None:
            raise UnknownDataRefError(data_id)
        return label

    def resolve(self, data_refs: list[str]) -> list[DataLabel]:
        return [self.require(ref) for ref in data_refs]

    def all_labels(self) -> list[DataLabel]:
        return list(self._labels.values())

    def __contains__(self, data_id: object) -> bool:
        return isinstance(data_id, str) and data_id in self._labels

    def __len__(self) -> int:
        return len(self._labels)
