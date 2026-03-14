from app.elaborations.models.dtos.configuration_operation_dto import (
    BuildResponseFromTemplateConfigurationOperationDto,
    DataConfigurationOperationDto,
    RunSuiteConfigurationOperationDto,
    SetResponseBodyConfigurationOperationDto,
    SetResponseHeaderConfigurationOperationDto,
    SetResponseStatusConfigurationOperationDto,
)
from app.elaborations.services.operations.build_response_from_template_operation_executor import (
    BuildResponseFromTemplateOperationExecutor,
)
from app.elaborations.services.operations.data_operation_executor import (
    DataOperationExecutor,
)
from app.elaborations.services.operations.run_suite_operation_executor import (
    RunSuiteOperationExecutor,
)
from app.elaborations.services.operations.set_response_body_operation_executor import (
    SetResponseBodyOperationExecutor,
)
from app.elaborations.services.operations.set_response_header_operation_executor import (
    SetResponseHeaderOperationExecutor,
)
from app.elaborations.services.operations.set_response_status_operation_executor import (
    SetResponseStatusOperationExecutor,
)
from elaborations.services.suite_runs.run_context import (
    bind_run_context,
    create_run_context,
)


def _disable_operation_logging(monkeypatch):
    import elaborations.services.operations.operation_executor as operation_executor_module

    monkeypatch.setattr(
        operation_executor_module.OperationExecutor,
        "log",
        classmethod(lambda cls, *args, **kwargs: None),
    )


def test_data_operation_writes_target_path(monkeypatch):
    _disable_operation_logging(monkeypatch)
    cfg = DataConfigurationOperationDto(
        data=[{"id": 1}],
        target="$.local.actualRows",
    )
    run_context = create_run_context(run_id="run-data-target")

    with bind_run_context(run_context):
        DataOperationExecutor().execute(None, "op-data", cfg, [])

    assert run_context.local_vars["actualRows"] == [{"id": 1}]


def test_run_suite_operation_writes_result_target(monkeypatch):
    _disable_operation_logging(monkeypatch)
    import elaborations.services.test_suites.test_suite_executor_service as suite_service_module

    monkeypatch.setattr(
        suite_service_module,
        "execute_test_suite_by_id",
        lambda suite_id, **kwargs: "suite-exec-1",
    )

    cfg = RunSuiteConfigurationOperationDto(
        suite_id="suite-1",
        result_target="$.local.trigger",
    )
    run_context = create_run_context(
        run_id="run-suite-target",
        event={"payload": {"id": 1}},
    )

    with bind_run_context(run_context):
        result = RunSuiteOperationExecutor().execute(
            None,
            "op-run-suite",
            cfg,
            [{"id": 1}],
        )

    assert result.result[0]["execution_id"] == "suite-exec-1"
    assert run_context.local_vars["trigger"]["execution_id"] == "suite-exec-1"
    assert run_context.local_vars["trigger"]["suite_id"] == "suite-1"


def test_mock_response_operations_update_response_draft(monkeypatch):
    _disable_operation_logging(monkeypatch)
    run_context = create_run_context(run_id="run-response")

    with bind_run_context(run_context):
        SetResponseStatusOperationExecutor().execute(
            None,
            "op-status",
            SetResponseStatusConfigurationOperationDto(status=202),
            [],
        )
        SetResponseHeaderOperationExecutor().execute(
            None,
            "op-header",
            SetResponseHeaderConfigurationOperationDto(
                name="X-Test",
                value="ok",
            ),
            [],
        )
        SetResponseBodyOperationExecutor().execute(
            None,
            "op-body",
            SetResponseBodyConfigurationOperationDto(body={"ok": True}),
            [],
        )
        BuildResponseFromTemplateOperationExecutor().execute(
            None,
            "op-template",
            BuildResponseFromTemplateConfigurationOperationDto(
                template={"payload": {"id": 10}},
                headers={"Content-Type": "application/json"},
                status=201,
            ),
            [],
        )

    assert run_context.response_draft["status"] == 201
    assert run_context.response_draft["headers"]["X-Test"] == "ok"
    assert run_context.response_draft["headers"]["Content-Type"] == "application/json"
    assert run_context.response_draft["body"] == {"payload": {"id": 10}}
