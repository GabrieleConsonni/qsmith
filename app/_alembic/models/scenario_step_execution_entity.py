from sqlalchemy import Column, DateTime, ForeignKey, Numeric, Text, func

from _alembic.constants import SCHEMA
from _alembic.models import Base
from _alembic.models.base_entity import BaseIdEntity


class ScenarioStepExecutionEntity(Base, BaseIdEntity):
    __tablename__ = "scenario_step_executions"
    scenario_execution_id = Column(
        Text,
        ForeignKey(f"{SCHEMA}.scenario_executions.id", ondelete="CASCADE"),
        nullable=False,
    )
    scenario_step_id = Column(Text, nullable=True)
    step_code = Column(Text, nullable=False)
    step_description = Column(Text, nullable=True)
    step_order = Column(Numeric, nullable=False, default=0)
    status = Column(Text, nullable=False, default="running")
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=False, default=func.now())
    finished_at = Column(DateTime, nullable=True)
