from intentfence_contracts import ActionReceipt, SecurityContext
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from .db_models import ReceiptRecord, SecurityContextRecord


class ReceiptRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def save(self, receipt: ActionReceipt) -> None:
        with Session(self.engine) as session:
            session.merge(
                ReceiptRecord(
                    receipt_id=receipt.receipt_id,
                    session_id=receipt.session_id,
                    intent_id=receipt.intent_id,
                    payload_json=receipt.model_dump_json(),
                    created_at=receipt.timestamp,
                )
            )
            session.commit()

    def get(self, receipt_id: str) -> ActionReceipt | None:
        with Session(self.engine) as session:
            record = session.get(ReceiptRecord, receipt_id)
            if record is None:
                return None
            return ActionReceipt.model_validate_json(record.payload_json)


class SecurityContextRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def upsert(self, context: SecurityContext) -> None:
        with Session(self.engine) as session:
            session.merge(
                SecurityContextRecord(
                    session_id=context.session_id,
                    intent_id=context.intent_id,
                    payload_json=context.model_dump_json(),
                    updated_at=context.last_updated_at,
                )
            )
            session.commit()

    def get(self, session_id: str) -> SecurityContext | None:
        with Session(self.engine) as session:
            record = session.get(SecurityContextRecord, session_id)
            if record is None:
                return None
            return SecurityContext.model_validate_json(record.payload_json)
