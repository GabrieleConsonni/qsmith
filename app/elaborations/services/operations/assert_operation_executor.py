from sqlalchemy.orm import Session

from elaborations.models.dtos.configuration_operation_dto import (
    AssertConfigurationOperationDto,
)
from elaborations.services.asserts.assert_evaluator_composite import evaluate_assert
from elaborations.services.operations.operation_executor import (
    ExecutionResultDto,
    OperationExecutor,
)
from logs.models.enums.log_level import LogLevel


class AssertOperationExecutor(OperationExecutor):
    def execute(
        self,
        session: Session,
        operation_id: str,
        cfg: AssertConfigurationOperationDto,
        data: list[dict],
    ) -> ExecutionResultDto:
        try:
            evaluate_assert(session, cfg, data)
        except Exception as exc:
            technical_message = str(exc)
            configured_message = str(cfg.error_message or "").strip()
            error_message = configured_message or technical_message
            self.log(
                operation_id,
                message=error_message,
                payload={"error": technical_message},
                level=LogLevel.ERROR,
            )
            raise ValueError(error_message) from exc

        message = (
            f"Assert '{cfg.assert_type}' passed for "
            f"'{cfg.evaluated_object_type}' data."
        )
        self.log(operation_id, message=message)
        return ExecutionResultDto(data=data, result=[{"message": message}])
