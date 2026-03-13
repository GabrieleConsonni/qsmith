from sqlalchemy.orm import Session

from elaborations.models.dtos.configuration_operation_dto import (
    DataConfigurationOperationDto,
)
from elaborations.services.operations.operation_executor import (
    ExecutionResultDto,
    OperationExecutor,
)
from elaborations.services.scenarios.run_context import write_context_path


class DataOperationExecutor(OperationExecutor):
    def execute(
        self,
        session: Session,
        operation_id: str,
        cfg: DataConfigurationOperationDto,
        data: list[dict],
    ) -> ExecutionResultDto:
        del session
        del data
        exported = cfg.data if isinstance(cfg.data, list) else []
        if cfg.target:
            write_context_path(cfg.target, exported)
        self.log(operation_id, f"Loaded {len(exported)} row(s) from inline data.")
        return ExecutionResultDto(
            data=exported,
            result=[{"message": f"Loaded {len(exported)} row(s) from inline data."}],
        )
