from sqlalchemy.orm import Session

from elaborations.models.dtos.configuration_operation_dto import (
    RunScenarioConfigurationOperationDto,
)
from elaborations.services.operations.operation_executor import (
    ExecutionResultDto,
    OperationExecutor,
)


class RunScenarioOperationExecutor(OperationExecutor):
    def execute(
        self,
        session: Session,
        operation_id: str,
        cfg: RunScenarioConfigurationOperationDto,
        data: list[dict],
    ) -> ExecutionResultDto:
        # Local import avoids circular dependency with step executor modules.
        from elaborations.services.scenarios.scenario_executor_service import (
            execute_scenario_by_id,
        )

        execution_id = execute_scenario_by_id(cfg.scenario_id)
        message = (
            f"Scenario '{cfg.scenario_id}' started with execution_id '{execution_id}'"
        )
        self.log(
            operation_id,
            message=message,
            payload={
                "scenario_id": cfg.scenario_id,
                "execution_id": execution_id,
            },
        )
        return ExecutionResultDto(
            data=data,
            result=[
                {
                    "message": message,
                    "scenario_id": cfg.scenario_id,
                    "execution_id": execution_id,
                }
            ],
        )
