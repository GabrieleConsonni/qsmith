from sqlalchemy import JSON, Column, ForeignKey, Numeric, Text

from _alembic.constants import SCHEMA
from _alembic.models import Base
from _alembic.models.code_desc_entity import CodeDescEntity


class MsApiOperationEntity(Base, CodeDescEntity):
    __tablename__ = "ms_api_operations"
    mock_server_api_id = Column(
        Text,
        ForeignKey(f"{SCHEMA}.mock_server_apis.id", ondelete="CASCADE"),
        nullable=False,
    )
    operation_type = Column(Text, nullable=False)
    configuration_json = Column(JSON, nullable=False)
    order = Column(Numeric, nullable=False, default=0)
