from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from _alembic.models.scenario_step_entity import ScenarioStepEntity
from elaborations.models.dtos.configuration_step_dtos import ConfigurationStepDtoTypes
from elaborations.services.alembic.step_operation_service import StepOperationService
from elaborations.services.operations.operation_executor_composite import execute_operations
from elaborations.services.scenarios.execution_event_bus import publish_runtime_log_event
from elaborations.services.scenarios.execution_runtime_context import bind_execution_context
from logs.models.dtos.log_dto import LogDto
from logs.models.enums.log_level import LogLevel
from logs.models.enums.log_subject_type import LogSubjectType
from logs.services.alembic.log_service import LogService


class StepExecutor(ABC):
    @classmethod
    def log(
        cls,
        step_id: str,
        message: str,
        payload: dict | list[dict] = None,
        level: LogLevel = LogLevel.INFO,
    ):
        log_dto = LogDto(
            subject_type=LogSubjectType.STEP_EXECUTION,
            subject=step_id,
            message=message,
            level=level,
            payload=payload,
        )
        LogService().log(log_dto)
        publish_runtime_log_event(
            subject_type=LogSubjectType.STEP_EXECUTION,
            subject=step_id,
            level=level,
            message=message,
            payload=payload,
        )

    @classmethod
    def execute_operations(cls, session: Session, step_id: str, data) -> list[dict[str, str]]:
        step_operations = cls.find_all_operations(session, step_id)
        with bind_execution_context(scenario_step_id=step_id):
            return execute_operations(session, step_operations, data).result

    @classmethod
    def find_all_operations(cls, session: Session, step_id: str):
        return StepOperationService().get_all_by_step(session, step_id)

    @abstractmethod
    def execute(
        self,
        session: Session,
        scenario_step: ScenarioStepEntity,
        cfg: ConfigurationStepDtoTypes,
    ) -> list[dict[str, str]]:
        pass
