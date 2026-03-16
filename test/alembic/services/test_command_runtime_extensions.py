from app.elaborations.models.dtos.configuration_command_dto import (
    DataConfigurationOperationDto,
    RunSuiteConfigurationOperationDto,
)
from app.elaborations.services.operations.init_constant_command_executor import (
    DataOperationExecutor,
)
from app.elaborations.services.operations.run_suite_command_executor import (
    RunSuiteOperationExecutor,
)
from elaborations.services.suite_runs.run_context import (
    bind_run_context,
    create_run_context,
)


def _disable_command_logging(monkeypatch):
    import elaborations.services.operations.command_executor as command_executor_module

    monkeypatch.setattr(
        command_executor_module.OperationExecutor,
        "log",
        classmethod(lambda cls, *args, **kwargs: None),
    )


def test_init_constant_command_writes_local_constant(monkeypatch):
    _disable_command_logging(monkeypatch)
    cfg = DataConfigurationOperationDto(
        data=[{"id": 1}],
        target="$.local.actualRows",
    )
    run_context = create_run_context(run_id="run-data-target")

    with bind_run_context(run_context):
        DataOperationExecutor().execute(None, "cmd-data", cfg, [])

    assert run_context.local_vars["actualRows"] == [{"id": 1}]


def test_run_suite_command_writes_result_target(monkeypatch):
    _disable_command_logging(monkeypatch)
    import elaborations.services.test_suites.test_suite_executor_service as suite_service_module

    monkeypatch.setattr(
        suite_service_module,
        "execute_test_suite_by_id",
        lambda suite_id, **kwargs: "suite-exec-1",
    )

    cfg = RunSuiteConfigurationOperationDto(
        suite_id="suite-1",
        constants=["order_id"],
        result_target="$.local.trigger",
    )
    run_context = create_run_context(
        run_id="run-suite-target",
        event={"payload": {"id": 1}},
    )
    run_context.local_scope["constants"]["order_id"] = "ORD-100"

    with bind_run_context(run_context):
        result = RunSuiteOperationExecutor().execute(
            None,
            "cmd-run-suite",
            cfg,
            [{"id": 1}],
        )

    assert result.result[0]["execution_id"] == "suite-exec-1"
    assert result.result[0]["constants"] == {"order_id": "ORD-100"}
    assert run_context.local_vars["trigger"]["execution_id"] == "suite-exec-1"
    assert run_context.local_vars["trigger"]["suite_id"] == "suite-1"
