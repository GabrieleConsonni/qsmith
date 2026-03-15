from sqlalchemy.orm import Session

from elaborations.models.dtos.configuration_operation_dto import (
    RunSuiteConfigurationOperationDto,
)
from elaborations.services.operations.operation_executor import (
    ExecutionResultDto,
    OperationExecutor,
)
from elaborations.services.suite_runs.run_context import (
    build_run_context_scope,
    get_run_context,
    write_context_path,
)
from elaborations.services.suite_runs.run_context_resolver import resolve_dynamic_value


class RunSuiteOperationExecutor(OperationExecutor):
    @staticmethod
    def _resolve_suite_id(session: Session, cfg: RunSuiteConfigurationOperationDto) -> str:
        return str(cfg.suite_id or "").strip()

    def execute(
        self,
        session: Session,
        operation_id: str,
        cfg: RunSuiteConfigurationOperationDto,
        data: list[dict],
    ) -> ExecutionResultDto:
        # Local import avoids circular dependency with test executor modules.
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
                "execution_id": execution_id,
                "init_vars": init_vars,
                "invocation_id": run_context.invocation_id if run_context else None,
            },
        )
        result_payload = {
            "suite_id": suite_id,
            "execution_id": execution_id,
            "init_vars": init_vars,
        }
        if cfg.result_target:
            write_context_path(cfg.result_target, result_payload)
        return ExecutionResultDto(
            data=data,
            result=[
                {
                    "message": message,
                    **result_payload,
                }
            ],
        )


RunSuiteOperationExecutor = RunSuiteOperationExecutor
