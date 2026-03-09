from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Text, func

from _alembic.constants import SCHEMA
from _alembic.models import Base
from _alembic.models.base_entity import BaseIdEntity


class ScenarioExecutionEntity(Base, BaseIdEntity):
    __tablename__ = "scenario_executions"
    scenario_id = Column(Text, ForeignKey(f"{SCHEMA}.scenarios.id", ondelete="CASCADE"), nullable=False)
    scenario_code = Column(Text, nullable=False)
    scenario_description = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="running")
    invocation_id = Column(
        Text,
        ForeignKey(f"{SCHEMA}.mock_server_invocations.id", ondelete="SET NULL"),
        nullable=True,
    )
    vars_init_json = Column(JSON, nullable=False, default=dict)
    result_json = Column(JSON, nullable=True)
    include_previous = Column(Boolean, nullable=False, default=False)
    requested_step_id = Column(Text, nullable=True)
    requested_step_code = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=False, default=func.now())
    finished_at = Column(DateTime, nullable=True)
