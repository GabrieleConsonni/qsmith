from sqlalchemy import Column, DateTime, ForeignKey, Numeric, Text, func

from _alembic.constants import SCHEMA
from _alembic.models import Base
from _alembic.models.base_entity import BaseIdEntity


class SuiteItemExecutionEntity(Base, BaseIdEntity):
    __tablename__ = "suite_item_executions"

    test_suite_execution_id = Column(
        Text,
        ForeignKey(f"{SCHEMA}.test_suite_executions.id", ondelete="CASCADE"),
        nullable=False,
    )
    suite_item_id = Column(Text, nullable=True)
    item_kind = Column(Text, nullable=False)
    hook_phase = Column(Text, nullable=True)
    item_description = Column(Text, nullable=True)
    position = Column(Numeric, nullable=False, default=0)
    status = Column(Text, nullable=False, default="running")
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=False, default=func.now())
    finished_at = Column(DateTime, nullable=True)
