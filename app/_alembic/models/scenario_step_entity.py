from sqlalchemy import JSON, Column, ForeignKey, Numeric, Text

from _alembic.constants import SCHEMA
from _alembic.models.base import Base
from _alembic.models.base_entity import BaseIdEntity
from elaborations.models.enums.on_failure import OnFailure


class ScenarioStepEntity(Base,BaseIdEntity):
    __tablename__ = "scenario_steps"
    scenario_id = Column(Text, ForeignKey(f"{SCHEMA}.scenarios.id", ondelete="CASCADE"), nullable=False)
    code = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    step_type = Column(Text, nullable=False)
    configuration_json = Column(JSON, nullable=False)
    order = Column(Numeric, nullable=False, default=0)
    on_failure = Column(Text, nullable=False, default=OnFailure.ABORT.value)
