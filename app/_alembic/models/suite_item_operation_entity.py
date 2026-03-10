from sqlalchemy import JSON, Column, ForeignKey, Numeric, Text

from _alembic.constants import SCHEMA
from _alembic.models import Base
from _alembic.models.base_entity import BaseIdEntity


class SuiteItemOperationEntity(Base, BaseIdEntity):
    __tablename__ = "suite_item_operations"

    suite_item_id = Column(
        Text,
        ForeignKey(f"{SCHEMA}.suite_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    code = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    operation_type = Column(Text, nullable=False)
    configuration_json = Column(JSON, nullable=False)
    order = Column(Numeric, nullable=False)
