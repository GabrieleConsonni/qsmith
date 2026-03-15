from sqlalchemy import Column, DateTime, ForeignKey, Numeric, Text, func

from _alembic.constants import SCHEMA
from _alembic.models import Base
from _alembic.models.base_entity import BaseIdEntity


class SuiteItemOperationExecutionEntity(Base, BaseIdEntity):
    __tablename__ = "suite_item_operation_executions"

    test_suite_execution_id = Column(
        Text,
        ForeignKey(f"{SCHEMA}.test_suite_executions.id", ondelete="CASCADE"),
        nullable=False,
    )
    suite_item_execution_id = Column(
        Text,
        ForeignKey(f"{SCHEMA}.suite_item_executions.id", ondelete="CASCADE"),
        nullable=False,
    )
    suite_item_id = Column(Text, nullable=True)
    suite_item_operation_id = Column(Text, nullable=True)
    operation_description = Column(Text, nullable=True)
    operation_order = Column(Numeric, nullable=False, default=0)
    status = Column(Text, nullable=False, default="running")
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=False, default=func.now())
    finished_at = Column(DateTime, nullable=True)
