from sqlalchemy.orm import Session

from elaborations.services.alembic.test_suite_service import TestSuiteService
from elaborations.models.dtos.configuration_operation_dto import (
    RunSuiteConfigurationOperationDto,
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


class RunSuiteOperationExecutor(OperationExecutor):
    @staticmethod
    def _resolve_suite_id(session: Session, cfg: RunSuiteConfigurationOperationDto) -> str:
        suite_id = str(cfg.suite_id or "").strip()
        if suite_id:
            return suite_id
        suite_code = str(cfg.suite_code or "").strip()
        suite_entity = TestSuiteService().get_by_code(session, suite_code)
        if suite_entity is None:
            raise ValueError(f"Test suite with code '{suite_code}' not found.")
        return str(suite_entity.id)

    def execute(
        self,
        session: Session,
        operation_id: str,
        cfg: RunSuiteConfigurationOperationDto,
        data: list[dict],
    ) -> ExecutionResultDto:
        # Local import avoids circular dependency with step executor modules.
        from elaborations.services.test_suites.test_suite_executor_service import (
            execute_test_suite_by_id,
        )

        suite_id = self._resolve_suite_id(session, cfg)
        run_context = get_run_context()
        scope = build_run_context_scope(run_context)
        init_vars = resolve_dynamic_value(cfg.init_vars or {}, scope)
        if not isinstance(init_vars, dict):
            raise ValueError("init_vars must resolve to a JSON object.")

        execution_id = execute_test_suite_by_id(
            suite_id,
            run_event=run_context.event if run_context else {},
            vars_init=init_vars,
            invocation_id=run_context.invocation_id if run_context else None,
        )
        message = (
            f"Test suite '{suite_id}' started with execution_id '{execution_id}'"
        )
        self.log(
            operation_id,
            message=message,
            payload={
                "suite_id": suite_id,
                "suite_code": str(cfg.suite_code or "").strip() or None,
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
                    "suite_id": suite_id,
                    "execution_id": execution_id,
                    "init_vars": init_vars,
                }
            ],
        )


RunScenarioOperationExecutor = RunSuiteOperationExecutor
