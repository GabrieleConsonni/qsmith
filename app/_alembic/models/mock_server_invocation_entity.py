from sqlalchemy import JSON, Column, DateTime, ForeignKey, Text, func

from _alembic.constants import SCHEMA
from _alembic.models import Base
from _alembic.models.base_entity import BaseIdEntity


class MockServerInvocationEntity(Base, BaseIdEntity):
    __tablename__ = "mock_server_invocations"
    mock_server_id = Column(
        Text,
        ForeignKey(f"{SCHEMA}.mock_servers.id", ondelete="CASCADE"),
        nullable=False,
    )
    mock_server_code = Column(Text, nullable=False)
    trigger_type = Column(Text, nullable=False)
    trigger_code = Column(Text, nullable=True)
    event_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
