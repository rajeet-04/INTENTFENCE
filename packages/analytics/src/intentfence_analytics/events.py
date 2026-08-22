from datetime import datetime
from enum import StrEnum

from intentfence_contracts import (
    DecisionSource,
    DecisionType,
    DestinationClass,
    ResourceClass,
    RuleStrength,
    Sensitivity,
)
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from sqlalchemy import JSON, Engine, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from .scenarios import GroundTruth, MutationType, ScenarioType


class CompletionStatus(StrEnum):
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    FAILED = "FAILED"


class BenchmarkEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1)
    created_at: AwareDatetime
    scenario_id: str = Field(min_length=1)
    scenario_type: ScenarioType
    attack_type: str | None = None
    mutation_type: MutationType | None = None
    ground_truth: GroundTruth | None = None
    step_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    intent_id: str = Field(min_length=1)
    tool: str = Field(min_length=1)
    resource_class: ResourceClass | None = None
    destination: str | None = None
    destination_class: DestinationClass | None = None
    data_refs: list[str] = Field(default_factory=list)
    data_sensitivity: Sensitivity | None = None
    matched_rules: list[str] = Field(default_factory=list)
    rule_strength: RuleStrength | None = None
    semantic_relevance_score: float | None = Field(default=None, ge=0.0, le=1.0)
    semantic_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    intent_drift_score: float | None = Field(default=None, ge=0.0, le=1.0)
    accumulated_risk: float | None = Field(default=None, ge=0.0, le=1.0)
    risk_score: float | None = Field(default=None, ge=0.0, le=1.0)
    chain_involved: bool = False
    decision_source: DecisionSource | None = None
    final_decision: DecisionType
    cloud_escalated: bool = False
    workflow_completed: bool = False
    completion_status: CompletionStatus | None = None
    latency_ms: int = Field(ge=0)
    model_used: str | None = None


class _Base(DeclarativeBase):
    pass


def _optional_str(value) -> str | None:
    return value.value if value is not None else None


class BenchmarkEventRow(_Base):
    __tablename__ = "benchmark_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[str] = mapped_column(String(40))
    scenario_id: Mapped[str] = mapped_column(String(128), index=True)
    scenario_type: Mapped[str] = mapped_column(String(64))
    attack_type: Mapped[str | None] = mapped_column(String(128))
    mutation_type: Mapped[str | None] = mapped_column(String(64))
    ground_truth: Mapped[str | None] = mapped_column(String(16))
    step_id: Mapped[str] = mapped_column(String(128))
    session_id: Mapped[str] = mapped_column(String(128))
    intent_id: Mapped[str] = mapped_column(String(128))
    tool: Mapped[str] = mapped_column(String(64))
    resource_class: Mapped[str | None] = mapped_column(String(32))
    destination: Mapped[str | None] = mapped_column(String(255))
    destination_class: Mapped[str | None] = mapped_column(String(32))
    data_refs: Mapped[list[str]] = mapped_column(JSON)
    data_sensitivity: Mapped[str | None] = mapped_column(String(16))
    matched_rules: Mapped[list[str]] = mapped_column(JSON)
    rule_strength: Mapped[str | None] = mapped_column(String(32))
    semantic_relevance_score: Mapped[float | None]
    semantic_confidence: Mapped[float | None]
    intent_drift_score: Mapped[float | None]
    accumulated_risk: Mapped[float | None]
    risk_score: Mapped[float | None]
    chain_involved: Mapped[bool]
    decision_source: Mapped[str | None] = mapped_column(String(32))
    final_decision: Mapped[str] = mapped_column(String(16))
    cloud_escalated: Mapped[bool]
    workflow_completed: Mapped[bool]
    completion_status: Mapped[str | None] = mapped_column(String(32))
    latency_ms: Mapped[int]
    model_used: Mapped[str | None] = mapped_column(String(128))


class EventStore:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        _Base.metadata.create_all(engine)

    @classmethod
    def from_url(cls, database_url: str) -> "EventStore":
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        return cls(create_engine(database_url, connect_args=connect_args))

    def append(self, event: BenchmarkEvent) -> None:
        self.append_many([event])

    def append_many(self, events: list[BenchmarkEvent]) -> None:
        with Session(self._engine) as session:
            session.add_all(_row_from_event(event) for event in events)
            session.commit()

    def list_events(self, run_id: str | None = None) -> list[BenchmarkEvent]:
        return self.list_run_events(run_id) if run_id else self._list_all()

    def list_run_ids(self) -> list[str]:
        with Session(self._engine) as session:
            rows = session.query(BenchmarkEventRow.run_id).distinct().all()
        return sorted(row.run_id for row in rows)

    def latest_run_id(self) -> str | None:
        with Session(self._engine) as session:
            return session.scalar(
                select(BenchmarkEventRow.run_id).order_by(BenchmarkEventRow.id.desc()).limit(1)
            )

    def _list_all(self) -> list[BenchmarkEvent]:
        with Session(self._engine) as session:
            rows = session.scalars(select(BenchmarkEventRow).order_by(BenchmarkEventRow.id)).all()
        return [_event_from_row(row) for row in rows]

    def list_run_events(self, run_id: str) -> list[BenchmarkEvent]:
        with Session(self._engine) as session:
            rows = session.scalars(
                select(BenchmarkEventRow)
                .where(BenchmarkEventRow.run_id == run_id)
                .order_by(BenchmarkEventRow.id)
            ).all()
        return [_event_from_row(row) for row in rows]


def _row_from_event(event: BenchmarkEvent) -> BenchmarkEventRow:
    return BenchmarkEventRow(
        run_id=event.run_id,
        created_at=event.created_at.isoformat(),
        scenario_id=event.scenario_id,
        scenario_type=event.scenario_type.value,
        attack_type=event.attack_type,
        mutation_type=_optional_str(event.mutation_type),
        ground_truth=_optional_str(event.ground_truth),
        step_id=event.step_id,
        session_id=event.session_id,
        intent_id=event.intent_id,
        tool=event.tool,
        resource_class=_optional_str(event.resource_class),
        destination=event.destination,
        destination_class=_optional_str(event.destination_class),
        data_refs=list(event.data_refs),
        data_sensitivity=_optional_str(event.data_sensitivity),
        matched_rules=list(event.matched_rules),
        rule_strength=_optional_str(event.rule_strength),
        semantic_relevance_score=event.semantic_relevance_score,
        semantic_confidence=event.semantic_confidence,
        intent_drift_score=event.intent_drift_score,
        accumulated_risk=event.accumulated_risk,
        risk_score=event.risk_score,
        chain_involved=event.chain_involved,
        decision_source=_optional_str(event.decision_source),
        final_decision=event.final_decision.value,
        cloud_escalated=event.cloud_escalated,
        workflow_completed=event.workflow_completed,
        completion_status=_optional_str(event.completion_status),
        latency_ms=event.latency_ms,
        model_used=event.model_used,
    )


def _event_from_row(row: BenchmarkEventRow) -> BenchmarkEvent:
    return BenchmarkEvent(
        run_id=row.run_id,
        created_at=datetime.fromisoformat(row.created_at),
        scenario_id=row.scenario_id,
        scenario_type=row.scenario_type,
        attack_type=row.attack_type,
        mutation_type=row.mutation_type,
        ground_truth=row.ground_truth,
        step_id=row.step_id,
        session_id=row.session_id,
        intent_id=row.intent_id,
        tool=row.tool,
        resource_class=row.resource_class,
        destination=row.destination,
        destination_class=row.destination_class,
        data_refs=list(row.data_refs),
        data_sensitivity=row.data_sensitivity,
        matched_rules=list(row.matched_rules),
        rule_strength=row.rule_strength,
        semantic_relevance_score=row.semantic_relevance_score,
        semantic_confidence=row.semantic_confidence,
        intent_drift_score=row.intent_drift_score,
        accumulated_risk=row.accumulated_risk,
        risk_score=row.risk_score,
        chain_involved=row.chain_involved,
        decision_source=row.decision_source,
        final_decision=row.final_decision,
        cloud_escalated=row.cloud_escalated,
        workflow_completed=row.workflow_completed,
        completion_status=row.completion_status,
        latency_ms=row.latency_ms,
        model_used=row.model_used,
    )
