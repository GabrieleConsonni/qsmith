from sqlalchemy.orm import Session

from elaborations.models.dtos.configuration_operation_dto import (
    SetResponseBodyConfigurationOperationDto,
)
from elaborations.services.operations.operation_executor import (
    ExecutionResultDto,
    OperationExecutor,
)
from elaborations.services.scenarios.run_context import set_response_body


class SetResponseBodyOperationExecutor(OperationExecutor):
    def execute(
        self,
        session: Session,
        operation_id: str,
        cfg: SetResponseBodyConfigurationOperationDto,
        data: list[dict],
    ) -> ExecutionResultDto:
        del session
        set_response_body(cfg.body)
        message = "Response body updated"
        self.log(operation_id, message)
        return ExecutionResultDto(data=data, result=[{"message": message, "body": cfg.body}])
