from datetime import UTC, datetime

from sqlalchemy.orm import Session

from _alembic.models.suite_item_operation_execution_entity import (
    SuiteItemOperationExecutionEntity,
)
from _alembic.models.suite_item_operation_entity import SuiteItemOperationEntity
from _alembic.models.test_operation_execution_entity import TestOperationExecutionEntity
from _alembic.models.test_operation_entity import TestOperationEntity
from elaborations.models.dtos.configuration_operation_dto import (
    AssertConfigurationOperationDto,
    BuildResponseFromTemplateConfigurationOperationDto,
    DataConfigurationOperationDto,
    DataFromDbConfigurationOperationDto,
    DataFromJsonArrayConfigurationOperationDto,
    DataFromQueueConfigurationOperationDto,
    ConfigurationOperationDto,
    ConfigurationOperationTypes,
    PublishConfigurationOperationDto,
    RunSuiteConfigurationOperationDto,
    SaveInternalDBConfigurationOperationDto,
    SaveToExternalDBConfigurationOperationDto,
    SetResponseBodyConfigurationOperationDto,
    SetResponseHeaderConfigurationOperationDto,
    SetResponseStatusConfigurationOperationDto,
    SetVarConfigurationOperationDto,
    SleepConfigurationOperationDto,
    convert_to_config_operation_type,
)
from elaborations.services.operations.data_from_db_operation_executor import (
    DataFromDbOperationExecutor,
)
from elaborations.services.operations.data_from_json_array_operation_executor import (
    DataFromJsonArrayOperationExecutor,
)
from elaborations.services.operations.data_from_queue_operation_executor import (
    DataFromQueueOperationExecutor,
)
from elaborations.services.operations.data_operation_executor import DataOperationExecutor
from elaborations.services.alembic.operation_service import OperationService
from elaborations.services.alembic.test_operation_execution_service import (
    TestOperationExecutionService,
)
from elaborations.services.alembic.suite_item_operation_execution_service import (
    SuiteItemOperationExecutionService,
)
from elaborations.services.operations.operation_executor import ExecutionResultDto, OperationExecutor
from elaborations.services.operations.assert_operation_executor import AssertOperationExecutor
from elaborations.services.operations.build_response_from_template_operation_executor import (
    BuildResponseFromTemplateOperationExecutor,
)
from elaborations.services.operations.operation_policy_validator import (
    validate_operation_policy,
)
from elaborations.services.operations.operation_scope import resolve_execution_scope
from elaborations.services.operations.publish_to_queue_operation_executor import PublishToQueueOperationExecutor
from elaborations.services.operations.run_suite_operation_executor import (
    RunSuiteOperationExecutor,
)
from elaborations.services.operations.save_to_external_db_operation_executor import SaveToExternalDbOperationExecutor
from elaborations.services.operations.save_to_internal_db_operation_executor import SaveInternalDbOperationExecutor
from elaborations.services.operations.set_response_body_operation_executor import (
    SetResponseBodyOperationExecutor,
)
from elaborations.services.operations.set_response_header_operation_executor import (
    SetResponseHeaderOperationExecutor,
)
from elaborations.services.operations.set_response_status_operation_executor import (
    SetResponseStatusOperationExecutor,
)
from elaborations.services.operations.set_var_operation_executor import SetVarOperationExecutor
from elaborations.services.operations.sleep_operation_executor import SleepOperationExecutor
from elaborations.services.suite_runs.execution_event_bus import (
    publish_execution_event,
    publish_runtime_log_event,
)
from elaborations.services.suite_runs.execution_runtime_context import (
    get_execution_id,
    get_suite_execution_id,
    get_suite_test_id,
    get_suite_test_execution_id,
    get_suite_item_execution_id,
    get_suite_item_id,
    get_test_suite_execution_id,
)
from elaborations.services.suite_runs.run_context import (
    build_run_context_scope,
)
from elaborations.services.suite_runs.run_context_resolver import resolve_dynamic_value
from logs.models.dtos.log_dto import LogDto
from logs.models.enums.log_level import LogLevel
from logs.models.enums.log_subject_type import LogSubjectType
from logs.services.alembic.log_service import LogService

_EXECUTOR_MAPPING: dict[type[ConfigurationOperationDto], type[OperationExecutor]] = {
    DataConfigurationOperationDto: DataOperationExecutor,
    DataFromJsonArrayConfigurationOperationDto: DataFromJsonArrayOperationExecutor,
    DataFromDbConfigurationOperationDto: DataFromDbOperationExecutor,
    DataFromQueueConfigurationOperationDto: DataFromQueueOperationExecutor,
    SleepConfigurationOperationDto: SleepOperationExecutor,
    PublishConfigurationOperationDto: PublishToQueueOperationExecutor,
    SaveInternalDBConfigurationOperationDto: SaveInternalDbOperationExecutor,
    SaveToExternalDBConfigurationOperationDto: SaveToExternalDbOperationExecutor,
    RunSuiteConfigurationOperationDto: RunSuiteOperationExecutor,
    SetVarConfigurationOperationDto: SetVarOperationExecutor,
    SetResponseStatusConfigurationOperationDto: SetResponseStatusOperationExecutor,
    SetResponseHeaderConfigurationOperationDto: SetResponseHeaderOperationExecutor,
    SetResponseBodyConfigurationOperationDto: SetResponseBodyOperationExecutor,
    BuildResponseFromTemplateConfigurationOperationDto: BuildResponseFromTemplateOperationExecutor,
    AssertConfigurationOperationDto: AssertOperationExecutor,
}


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def log(message: str, level: LogLevel = LogLevel.INFO):
    log_dto = LogDto(
        subject_type=LogSubjectType.OPERATION_EXECUTION,
        subject="N/A",
        message=message,
        level=level,
    )
    LogService().log(log_dto)
    publish_runtime_log_event(
        subject_type=LogSubjectType.OPERATION_EXECUTION,
        subject="N/A",
        level=level,
        message=message,
    )


def _resolve_operation_payload(
    session: Session,
    operation_input: TestOperationEntity | SuiteItemOperationEntity | str,
) -> tuple[str, dict, str, str, int]:
    if isinstance(operation_input, (TestOperationEntity, SuiteItemOperationEntity)):
        operation_id = str(operation_input.id)
        cfg_json = (
            operation_input.configuration_json
            if isinstance(operation_input.configuration_json, dict)
            else {}
        )
        operation_code = str(operation_input.code or operation_id)
        operation_description = str(operation_input.description or "")
        operation_order = int(operation_input.order or 0)
        return operation_id, cfg_json, operation_code, operation_description, operation_order

    # Backward compatibility for old code paths that still pass operation ids.
    operation_id = str(operation_input or "").strip()
    operation_entity = OperationService().get_by_id(session, operation_id)
    if not operation_entity:
        message = f"Operation with id '{operation_id}' not found"
        log(message, level=LogLevel.ERROR)
        raise ValueError(message)
    cfg_json = (
        operation_entity.configuration_json
        if isinstance(operation_entity.configuration_json, dict)
        else {}
    )
    operation_code = str(operation_entity.code or operation_id)
    operation_description = str(operation_entity.description or "")
    operation_order = 0
    return operation_id, cfg_json, operation_code, operation_description, operation_order


def execute_operations(
    session: Session,
    operations: list[TestOperationEntity] | list[SuiteItemOperationEntity] | list[str],
    data: list[dict],
    execution_scope: str | None = None,
) -> ExecutionResultDto:
    execution_result = ExecutionResultDto(data=data, result=[])
    operation_execution_service = TestOperationExecutionService()
    suite_operation_execution_service = SuiteItemOperationExecutionService()
    resolved_execution_scope = resolve_execution_scope(execution_scope)

    log(f"Starting execution {len(operations)} operations")

    for operation_input in operations:
        op_id, op_cfg_json, op_code, op_description, op_order = _resolve_operation_payload(
            session,
            operation_input,
        )

        suite_execution_id = str(get_suite_execution_id() or "").strip()
        suite_test_execution_id = str(get_suite_test_execution_id() or "").strip()
        suite_test_id = str(get_suite_test_id() or "").strip()
        test_suite_execution_id = str(get_test_suite_execution_id() or "").strip()
        suite_item_execution_id = str(get_suite_item_execution_id() or "").strip()
        suite_item_id = str(get_suite_item_id() or "").strip()

        operation_execution_id = ""
        suite_operation_execution_id = ""
        if suite_execution_id and suite_test_execution_id:
            operation_execution_id = operation_execution_service.insert(
                session,
                TestOperationExecutionEntity(
                    suite_execution_id=suite_execution_id,
                    suite_test_execution_id=suite_test_execution_id,
                    suite_test_id=suite_test_id or None,
                    test_operation_id=op_id or None,
                    operation_code=op_code,
                    operation_description=op_description,
                    operation_order=op_order,
                    status="running",
                ),
            )
        if test_suite_execution_id and suite_item_execution_id:
            suite_operation_execution_id = suite_operation_execution_service.insert(
                session,
                SuiteItemOperationExecutionEntity(
                    test_suite_execution_id=test_suite_execution_id,
                    suite_item_execution_id=suite_item_execution_id,
                    suite_item_id=suite_item_id or None,
                    suite_item_operation_id=op_id or None,
                    operation_code=op_code,
                    operation_description=op_description,
                    operation_order=op_order,
                    status="running",
                ),
            )

        resolved_cfg_json = resolve_dynamic_value(op_cfg_json, build_run_context_scope())
        cfg = convert_to_config_operation_type(resolved_cfg_json)
        contract = None
        try:
            contract = validate_operation_policy(cfg, resolved_execution_scope)
            new_execution_result = execute_operation(session, op_id, cfg, execution_result.data)
            execution_result.extend(new_execution_result)
            if operation_execution_id:
                operation_execution_service.update(
                    session,
                    operation_execution_id,
                    status="success",
                    error_message=None,
                    finished_at=_utc_now(),
                )
            if suite_operation_execution_id:
                suite_operation_execution_service.update(
                    session,
                    suite_operation_execution_id,
                    status="success",
                    error_message=None,
                    finished_at=_utc_now(),
                )
            execution_id = get_execution_id()
            if execution_id:
                publish_execution_event(
                    execution_id,
                    "operation_finished",
                    {
                        "suite_test_id": suite_test_id,
                        "suite_test_execution_id": suite_test_execution_id or None,
                        "test_operation_execution_id": operation_execution_id or None,
                        "suite_item_id": suite_item_id or None,
                        "suite_item_execution_id": suite_item_execution_id or None,
                        "suite_item_operation_execution_id": suite_operation_execution_id or None,
                        "operation_id": op_id,
                        "operation_code": op_code,
                        "operation_scope": resolved_execution_scope,
                        "operation_family": contract.family if contract else None,
                        "status": "success",
                        "result": new_execution_result.result,
                    },
                )
        except Exception as op_exception:
            if operation_execution_id:
                operation_execution_service.update(
                    session,
                    operation_execution_id,
                    status="error",
                    error_message=str(op_exception),
                    finished_at=_utc_now(),
                )
            if suite_operation_execution_id:
                suite_operation_execution_service.update(
                    session,
                    suite_operation_execution_id,
                    status="error",
                    error_message=str(op_exception),
                    finished_at=_utc_now(),
                )
            execution_id = get_execution_id()
            if execution_id:
                publish_execution_event(
                    execution_id,
                    "operation_finished",
                    {
                        "suite_test_id": suite_test_id,
                        "suite_test_execution_id": suite_test_execution_id or None,
                        "test_operation_execution_id": operation_execution_id or None,
                        "suite_item_id": suite_item_id or None,
                        "suite_item_execution_id": suite_item_execution_id or None,
                        "suite_item_operation_execution_id": suite_operation_execution_id or None,
                        "operation_id": op_id,
                        "operation_code": op_code,
                        "operation_scope": resolved_execution_scope,
                        "operation_family": contract.family if contract else None,
                        "status": "error",
                        "error": str(op_exception),
                    },
                )
            raise

    return execution_result


def execute_operation(
    session: Session,
    operation_id: str,
    cfg: ConfigurationOperationTypes,
    data: list[dict],
) -> ExecutionResultDto:
    clazz = _EXECUTOR_MAPPING.get(type(cfg))
    if clazz is None:
        supported_types = list(_EXECUTOR_MAPPING.keys())
        message = f"Unsupported operation type: {cfg}. Supported types: {supported_types}"
        log(message, level=LogLevel.ERROR)
        raise ValueError(message)
    operation_executor = clazz()
    return operation_executor.execute(session, operation_id, cfg, data)
