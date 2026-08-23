import json
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4


@dataclass
class SandboxEnvironment:
    """Disposable state container for real demo tool side effects.

    Raw fixture/payload values live only inside this sandbox. Gateway receipts and
    security events receive only metadata returned by the runtime handlers.
    """

    root: Path
    workspace: Path
    outbox_file: Path
    attacker_log: Path
    _payloads: dict[str, str] = field(default_factory=dict, repr=False)

    @classmethod
    def create(cls, root: Path) -> "SandboxEnvironment":
        resolved = root.resolve()
        resolved.mkdir(parents=True, exist_ok=True)
        workspace = resolved / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)
        outbox = resolved / "outbox.jsonl"
        attacker = resolved / "attacker.jsonl"
        outbox.touch(exist_ok=True)
        attacker.touch(exist_ok=True)
        return cls(
            root=resolved,
            workspace=workspace,
            outbox_file=outbox,
            attacker_log=attacker,
        )

    def resolve(self, relative_path: str) -> Path:
        if not relative_path or not relative_path.strip():
            raise ValueError("sandbox path is required")
        candidate = (self.root / relative_path).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise ValueError("sandbox path escapes configured root")
        return candidate

    def write_fixture(self, relative_path: str, content: str) -> Path:
        target = self.resolve(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def read_fixture(self, relative_path: str) -> str:
        return self.resolve(relative_path).read_text(encoding="utf-8")

    def store_payload(self, content: str) -> str:
        data_ref = f"sandbox-data-{uuid4().hex}"
        self._payloads[data_ref] = content
        return data_ref

    def payload(self, data_ref: str) -> str:
        try:
            return self._payloads[data_ref]
        except KeyError as exc:
            raise ValueError(f"unknown sandbox payload reference: {data_ref}") from exc

    def take_payload(self, data_ref: str) -> str:
        try:
            return self._payloads.pop(data_ref)
        except KeyError as exc:
            raise ValueError(f"unknown sandbox payload reference: {data_ref}") from exc

    def append_outbox(self, record: dict[str, object]) -> None:
        with self.outbox_file.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True) + "\n")

    def outbox_records(self) -> list[dict[str, object]]:
        return self._read_jsonl(self.outbox_file)

    def append_attacker_record(self, record: dict[str, object]) -> None:
        with self.attacker_log.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True) + "\n")

    def attacker_records(self) -> list[dict[str, object]]:
        return self._read_jsonl(self.attacker_log)

    @staticmethod
    def _read_jsonl(path: Path) -> list[dict[str, object]]:
        records: list[dict[str, object]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                value = json.loads(line)
                if isinstance(value, dict):
                    records.append(value)
        return records
