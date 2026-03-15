from sqlalchemy import JSON, Column, ForeignKey, Numeric, Text

from _alembic.constants import SCHEMA
from _alembic.models import Base
from _alembic.models.code_desc_entity import CodeDescEntity


class MsQueueOperationEntity(Base, CodeDescEntity):
    __tablename__ = "ms_queue_operations"
    mock_server_queue_id = Column(
        Text,
        ForeignKey(f"{SCHEMA}.mock_server_queues.id", ondelete="CASCADE"),
        nullable=False,
    )
    operation_type = Column(Text, nullable=False)
    configuration_json = Column(JSON, nullable=False)
    order = Column(Numeric, nullable=False, default=0)
