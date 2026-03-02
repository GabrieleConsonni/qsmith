from sqlalchemy.orm import InstrumentedAttribute, Session

from _alembic.models.base_entity import BaseIdEntity
from _alembic.models.step_operation_execution_entity import StepOperationExecutionEntity
from _alembic.services.base_id_service import BaseIdEntityService


class StepOperationExecutionService(BaseIdEntityService):
    def get_entity_class(self) -> type[BaseIdEntity]:
        return StepOperationExecutionEntity

    def get_all_by_step_execution_id(
        self,
        session: Session,
        scenario_step_execution_id: str,
    ) -> list[StepOperationExecutionEntity]:
        scenario_step_execution_id_attr: InstrumentedAttribute = (
            StepOperationExecutionEntity.scenario_step_execution_id
        )
        return (
            session.query(StepOperationExecutionEntity)
            .filter(scenario_step_execution_id_attr == scenario_step_execution_id)
            .order_by(
                StepOperationExecutionEntity.operation_order,
                StepOperationExecutionEntity.started_at,
                StepOperationExecutionEntity.id,
            )
            .all()
        )
