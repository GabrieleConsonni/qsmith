from sqlalchemy.orm import Session

from _alembic.models.step_operation_entity import StepOperationEntity
from elaborations.models.dtos.configuration_operation_dto import (
    ConfigurationOperationDto,
    ConfigurationOperationTypes,
    PublishConfigurationOperationDto,
    SaveInternalDBConfigurationOperationDto,
    SaveToExternalDBConfigurationOperationDto,
    convert_to_config_operation_type,
)
from elaborations.services.alembic.operation_service import OperationService
from elaborations.services.operations.operation_executor import ExecutionResultDto, OperationExecutor
from elaborations.services.operations.publish_to_queue_operation_executor import PublishToQueueOperationExecutor
from elaborations.services.operations.save_to_external_db_operation_executor import SaveToExternalDbOperationExecutor
from elaborations.services.operations.save_to_internal_db_operation_executor import SaveInternalDbOperationExecutor
from elaborations.services.scenarios.execution_event_bus import (
    publish_execution_event,
    publish_runtime_log_event,
)
from elaborations.services.scenarios.execution_runtime_context import (
    get_execution_id,
    get_scenario_step_id,
)
from logs.models.dtos.log_dto import LogDto
from logs.models.enums.log_level import LogLevel
from logs.models.enums.log_subject_type import LogSubjectType
from logs.services.alembic.log_service import LogService

_EXECUTOR_MAPPING: dict[type[ConfigurationOperationDto], type[OperationExecutor]] = {
    PublishConfigurationOperationDto: PublishToQueueOperationExecutor,
    SaveInternalDBConfigurationOperationDto: SaveInternalDbOperationExecutor,
    SaveToExternalDBConfigurationOperationDto: SaveToExternalDbOperationExecutor,
}


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
    operation_input: StepOperationEntity | str,
) -> tuple[str, dict, str]:
    if isinstance(operation_input, StepOperationEntity):
        operation_id = str(operation_input.id)
        cfg_json = (
            operation_input.configuration_json
            if isinstance(operation_input.configuration_json, dict)
            else {}
        )
        operation_code = str(operation_input.code or operation_id)
        return operation_id, cfg_json, operation_code

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
    return operation_id, cfg_json, operation_code


def execute_operations(
    session: Session,
    operations: list[StepOperationEntity] | list[str],
    data: list[dict],
) -> ExecutionResultDto:
    execution_result = ExecutionResultDto(data=data, result=[])

    log(f"Starting execution {len(operations)} operations")

    for operation_input in operations:
        op_id, op_cfg_json, op_code = _resolve_operation_payload(session, operation_input)
        cfg = convert_to_config_operation_type(op_cfg_json)
        try:
            new_execution_result = execute_operation(session, op_id, cfg, execution_result.data)
            execution_result.extend(new_execution_result)
            execution_id = get_execution_id()
            if execution_id:
                publish_execution_event(
                    execution_id,
                    "operation_finished",
                    {
                        "scenario_step_id": get_scenario_step_id(),
                        "operation_id": op_id,
                        "operation_code": op_code,
                        "status": "success",
                        "result": new_execution_result.result,
                    },
                )
        except Exception as op_exception:
            execution_id = get_execution_id()
            if execution_id:
                publish_execution_event(
                    execution_id,
                    "operation_finished",
                    {
                        "scenario_step_id": get_scenario_step_id(),
                        "operation_id": op_id,
                        "operation_code": op_code,
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
