from _alembic.models.base_entity import BaseIdEntity
from _alembic.models.step_entity import StepEntity
from _alembic.services.base_id_service import BaseIdEntityService
from sqlalchemy import or_
from sqlalchemy.orm import Session

class StepService(BaseIdEntityService):
    def get_entity_class(self) -> type[BaseIdEntity]:
        return StepEntity

    def get_filtered_query(self, session: Session, search: str = ""):
        query = session.query(StepEntity)
        search_value = str(search or "").strip()
        if search_value:
            search_pattern = f"%{search_value}%"
            query = query.filter(
                or_(
                    StepEntity.code.ilike(search_pattern),
                    StepEntity.description.ilike(search_pattern),
                )
            )
        return query.order_by(StepEntity.code.asc())
