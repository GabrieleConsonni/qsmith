from _alembic.models.base_entity import BaseIdEntity
from _alembic.models.operation_entity import OperationEntity
from _alembic.services.base_id_service import BaseIdEntityService
from sqlalchemy import or_
from sqlalchemy.orm import Session


class OperationService(BaseIdEntityService):
    def get_entity_class(self) -> type[BaseIdEntity]:
        return OperationEntity

    def get_filtered_query(self, session: Session, search: str = ""):
        query = session.query(OperationEntity)
        search_value = str(search or "").strip()
        if search_value:
            search_pattern = f"%{search_value}%"
            query = query.filter(OperationEntity.description.ilike(search_pattern))
        return query.order_by(OperationEntity.description.asc(), OperationEntity.id.asc())
