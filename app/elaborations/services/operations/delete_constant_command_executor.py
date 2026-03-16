from sqlalchemy.orm import Session

from elaborations.models.dtos.configuration_command_dto import (
    DeleteConstantConfigurationCommandDto,
)
from elaborations.services.operations.command_executor import (
    ExecutionResultDto,
    OperationExecutor,
)
from elaborations.services.suite_runs.run_context import remove_context_path


class DeleteConstantOperationExecutor(OperationExecutor):
    def execute(
        self,
        session: Session,
        operation_id: str,
        cfg: DeleteConstantConfigurationCommandDto,
        data,
    ) -> ExecutionResultDto:
        del session
        target_path = f"$.{cfg.context}.constants.{cfg.name}"
        remove_context_path(target_path)
        message = f"Deleted constant '{cfg.name}' from context '{cfg.context}'."
        self.log(operation_id, message)
        return ExecutionResultDto(
            data=data,
            result=[
                {
                    "message": message,
                    "name": cfg.name,
                    "context": cfg.context,
                }
            ],
        )

