from sqlalchemy import Column, ForeignKey, Numeric, Text

from _alembic.constants import SCHEMA
from _alembic.models.base import Base
from _alembic.models.base_entity import BaseIdEntity
from elaborations.models.enums.on_failure import OnFailure
from elaborations.models.enums.suite_item_kind import SuiteItemKind


class SuiteItemEntity(Base, BaseIdEntity):
    __tablename__ = "suite_items"

    test_suite_id = Column(
        Text,
        ForeignKey(f"{SCHEMA}.test_suites.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind = Column(Text, nullable=False, default=SuiteItemKind.TEST.value)
    hook_phase = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    position = Column(Numeric, nullable=False, default=0)
    on_failure = Column(Text, nullable=False, default=OnFailure.ABORT.value)
