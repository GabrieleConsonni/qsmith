from sqlalchemy.orm import Session

from elaborations.models.dtos.configuration_operation_dto import (
    SetResponseStatusConfigurationOperationDto,
)
from elaborations.services.operations.operation_executor import (
    ExecutionResultDto,
    OperationExecutor,
)
from elaborations.services.scenarios.run_context import set_response_status


class SetResponseStatusOperationExecutor(OperationExecutor):
    def execute(
        self,
        session: Session,
        operation_id: str,
        cfg: SetResponseStatusConfigurationOperationDto,
        data: list[dict],
    ) -> ExecutionResultDto:
        del session
        status_value = cfg.status if cfg.status is not None else 200
        try:
            normalized_status = int(status_value)
        except (TypeError, ValueError):
            normalized_status = 200
        set_response_status(normalized_status)
        message = f"Response status set to {normalized_status}"
        self.log(operation_id, message)
        return ExecutionResultDto(data=data, result=[{"message": message, "status": normalized_status}])
