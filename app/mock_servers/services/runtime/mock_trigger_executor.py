from typing import Any

from _alembic.models.step_operation_entity import StepOperationEntity
from _alembic.services.session_context_manager import managed_session
from elaborations.services.operations.operation_executor_composite import execute_operations
from logs.models.enums.log_level import LogLevel
from mock_servers.models.runtime_models import MockOperationSnapshot
from mock_servers.services.runtime.mock_runtime_logger import log_mock_server_event


def _normalize_input_data(data: Any) -> list[dict]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def _to_step_operation_snapshot(
    source_id: str,
    operation: MockOperationSnapshot,
) -> StepOperationEntity:
    snapshot = StepOperationEntity()
    snapshot.id = operation.id
    snapshot.scenario_step_id = source_id or "mock-runtime"
    snapshot.code = operation.code
    snapshot.description = operation.description
    snapshot.operation_type = operation.operation_type
    snapshot.configuration_json = operation.configuration_json
    snapshot.order = operation.order
    return snapshot


def execute_mock_operations(
    *,
    mock_server_id: str,
    trigger_id: str,
    source_type: str,
    source_ref: str,
    operations: list[MockOperationSnapshot],
    data: Any,
):
    normalized_data = _normalize_input_data(data)
    snapshots = [
        _to_step_operation_snapshot(source_ref, operation)
        for operation in operations or []
    ]
    if not snapshots:
        log_mock_server_event(
            mock_server_id,
            f"[{trigger_id}] No operations configured for {source_type} trigger.",
        )
        return

    try:
        with managed_session() as session:
            execute_operations(session, snapshots, normalized_data)
        log_mock_server_event(
            mock_server_id,
            f"[{trigger_id}] Executed {len(snapshots)} operation(s) for {source_type} trigger.",
            payload={
                "trigger_id": trigger_id,
                "source_type": source_type,
                "source_ref": source_ref,
                "operations": len(snapshots),
            },
        )
    except Exception as exc:
        log_mock_server_event(
            mock_server_id,
            f"[{trigger_id}] Error executing operations for {source_type}: {str(exc)}",
            level=LogLevel.ERROR,
            payload={
                "trigger_id": trigger_id,
                "source_type": source_type,
                "source_ref": source_ref,
                "error": str(exc),
            },
        )
