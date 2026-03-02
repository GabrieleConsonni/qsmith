from sqlalchemy import desc
from sqlalchemy.orm import InstrumentedAttribute, Session

from _alembic.models.base_entity import BaseIdEntity
from _alembic.models.scenario_execution_entity import ScenarioExecutionEntity
from _alembic.services.base_id_service import BaseIdEntityService


class ScenarioExecutionService(BaseIdEntityService):
    def get_entity_class(self) -> type[BaseIdEntity]:
        return ScenarioExecutionEntity

    def get_all_ordered(self, session: Session, limit: int = 50) -> list[ScenarioExecutionEntity]:
        query = session.query(ScenarioExecutionEntity).order_by(
            desc(ScenarioExecutionEntity.started_at),
            desc(ScenarioExecutionEntity.id),
        )
        if limit and limit > 0:
            query = query.limit(limit)
        return query.all()

    def get_all_by_scenario_id(
        self,
        session: Session,
        scenario_id: str,
        limit: int = 50,
    ) -> list[ScenarioExecutionEntity]:
        scenario_id_attr: InstrumentedAttribute = ScenarioExecutionEntity.scenario_id
        query = (
            session.query(ScenarioExecutionEntity)
            .filter(scenario_id_attr == scenario_id)
            .order_by(
                desc(ScenarioExecutionEntity.started_at),
                desc(ScenarioExecutionEntity.id),
            )
        )
        if limit and limit > 0:
            query = query.limit(limit)
        return query.all()
