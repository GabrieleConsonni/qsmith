from sqlalchemy import Column, DateTime, ForeignKey, Numeric, Text, func

from _alembic.constants import SCHEMA
from _alembic.models import Base
from _alembic.models.base_entity import BaseIdEntity


class StepOperationExecutionEntity(Base, BaseIdEntity):
    __tablename__ = "step_operation_executions"
    scenario_execution_id = Column(
        Text,
        ForeignKey(f"{SCHEMA}.scenario_executions.id", ondelete="CASCADE"),
        nullable=False,
    )
    scenario_step_execution_id = Column(
        Text,
        ForeignKey(f"{SCHEMA}.scenario_step_executions.id", ondelete="CASCADE"),
        nullable=False,
    )
    scenario_step_id = Column(Text, nullable=True)
    step_operation_id = Column(Text, nullable=True)
    operation_code = Column(Text, nullable=False)
    operation_description = Column(Text, nullable=True)
    operation_order = Column(Numeric, nullable=False, default=0)
    status = Column(Text, nullable=False, default="running")
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=False, default=func.now())
    finished_at = Column(DateTime, nullable=True)
