from sqlalchemy.orm import InstrumentedAttribute, Session

from _alembic.models.base_entity import BaseIdEntity
from _alembic.models.scenario_step_execution_entity import ScenarioStepExecutionEntity
from _alembic.services.base_id_service import BaseIdEntityService


class ScenarioStepExecutionService(BaseIdEntityService):
    def get_entity_class(self) -> type[BaseIdEntity]:
        return ScenarioStepExecutionEntity

    def get_all_by_execution_id(
        self,
        session: Session,
        scenario_execution_id: str,
    ) -> list[ScenarioStepExecutionEntity]:
        scenario_execution_id_attr: InstrumentedAttribute = (
            ScenarioStepExecutionEntity.scenario_execution_id
        )
        return (
            session.query(ScenarioStepExecutionEntity)
            .filter(scenario_execution_id_attr == scenario_execution_id)
            .order_by(
                ScenarioStepExecutionEntity.step_order,
                ScenarioStepExecutionEntity.started_at,
                ScenarioStepExecutionEntity.id,
            )
            .all()
        )
