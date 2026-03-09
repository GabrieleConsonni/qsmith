from sqlalchemy.orm import Session

from elaborations.services.alembic.scenario_service import ScenarioService
from elaborations.models.dtos.configuration_operation_dto import (
    RunScenarioConfigurationOperationDto,
)
from elaborations.services.operations.operation_executor import (
    ExecutionResultDto,
    OperationExecutor,
)
from elaborations.services.scenarios.run_context import (
    build_run_context_scope,
    get_run_context,
)
from elaborations.services.scenarios.run_context_resolver import resolve_dynamic_value


class RunScenarioOperationExecutor(OperationExecutor):
    @staticmethod
    def _resolve_scenario_id(session: Session, cfg: RunScenarioConfigurationOperationDto) -> str:
        scenario_id = str(cfg.scenario_id or "").strip()
        if scenario_id:
            return scenario_id
        scenario_code = str(cfg.scenario_code or "").strip()
        scenario_entity = ScenarioService().get_by_code(session, scenario_code)
        if scenario_entity is None:
            raise ValueError(f"Scenario with code '{scenario_code}' not found.")
        return str(scenario_entity.id)

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

        scenario_id = self._resolve_scenario_id(session, cfg)
        run_context = get_run_context()
        scope = build_run_context_scope(run_context)
        init_vars = resolve_dynamic_value(cfg.init_vars or {}, scope)
        if not isinstance(init_vars, dict):
            raise ValueError("init_vars must resolve to a JSON object.")

        execution_id = execute_scenario_by_id(
            scenario_id,
            run_event=run_context.event if run_context else {},
            vars_init=init_vars,
            invocation_id=run_context.invocation_id if run_context else None,
        )
        message = (
            f"Scenario '{scenario_id}' started with execution_id '{execution_id}'"
        )
        self.log(
            operation_id,
            message=message,
            payload={
                "scenario_id": scenario_id,
                "scenario_code": str(cfg.scenario_code or "").strip() or None,
                "execution_id": execution_id,
                "init_vars": init_vars,
                "invocation_id": run_context.invocation_id if run_context else None,
            },
        )
        return ExecutionResultDto(
            data=data,
            result=[
                {
                    "message": message,
                    "scenario_id": scenario_id,
                    "execution_id": execution_id,
                    "init_vars": init_vars,
                }
            ],
        )
