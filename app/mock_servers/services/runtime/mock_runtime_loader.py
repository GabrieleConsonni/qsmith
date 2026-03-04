from typing import Any

from _alembic.models.mock_server_entity import MockServerEntity
from mock_servers.models.runtime_models import (
    MockApiRoute,
    MockOperationSnapshot,
    MockQueueBinding,
    MockRuntimeServer,
)
from mock_servers.services.alembic.mock_server_api_service import MockServerApiService
from mock_servers.services.alembic.mock_server_queue_service import MockServerQueueService
from mock_servers.services.alembic.ms_api_operation_service import MsApiOperationService
from mock_servers.services.alembic.ms_queue_operation_service import MsQueueOperationService


def _safe_cfg(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _normalize_path(path: object) -> str:
    raw = str(path or "").strip()
    if not raw:
        return "/"
    if not raw.startswith("/"):
        raw = f"/{raw}"
    if len(raw) > 1:
        raw = raw.rstrip("/")
    return raw


def _normalize_endpoint(endpoint: object) -> str:
    return str(endpoint or "").strip().strip("/").lower()


def _build_operation_snapshot(entity) -> MockOperationSnapshot:
    return MockOperationSnapshot(
        id=str(entity.id or ""),
        code=str(entity.code or ""),
        description=str(entity.description or ""),
        operation_type=str(entity.operation_type or ""),
        configuration_json=_safe_cfg(entity.configuration_json),
        order=int(entity.order or 0),
    )


def load_runtime_server(session, entity: MockServerEntity) -> MockRuntimeServer:
    endpoint = _normalize_endpoint(entity.endpoint)
    apis_entities = MockServerApiService().get_all_by_server_id(session, entity.id)
    queue_entities = MockServerQueueService().get_all_by_server_id(session, entity.id)

    api_routes: list[MockApiRoute] = []
    for api_entity in apis_entities:
        api_cfg = _safe_cfg(api_entity.configuration_json)
        operations = MsApiOperationService().get_all_by_api_id(session, api_entity.id)
        api_routes.append(
            MockApiRoute(
                id=str(api_entity.id or ""),
                code=str(api_entity.code or ""),
                description=str(api_entity.description or ""),
                order=int(api_entity.order or 0),
                method=str(api_entity.method or api_cfg.get("method") or "GET").strip().upper(),
                path=_normalize_path(api_entity.path or api_cfg.get("path")),
                params=api_cfg.get("params") if isinstance(api_cfg.get("params"), dict) else {},
                headers=api_cfg.get("headers") if isinstance(api_cfg.get("headers"), dict) else {},
                body=api_cfg.get("body"),
                body_match=str(api_cfg.get("body_match") or "contains").strip().lower(),
                priority=int(api_cfg.get("priority") or 0),
                response_status=max(int(api_cfg.get("response_status") or 200), 100),
                response_headers=(
                    api_cfg.get("response_headers")
                    if isinstance(api_cfg.get("response_headers"), dict)
                    else {}
                ),
                response_body=api_cfg.get("response_body"),
                operations=[
                    _build_operation_snapshot(operation_entity)
                    for operation_entity in operations
                ],
            )
        )

    queue_bindings: list[MockQueueBinding] = []
    for queue_entity in queue_entities:
        queue_cfg = _safe_cfg(queue_entity.configuration_json)
        operations = MsQueueOperationService().get_all_by_queue_binding_id(
            session,
            queue_entity.id,
        )
        queue_bindings.append(
            MockQueueBinding(
                id=str(queue_entity.id or ""),
                code=str(queue_entity.code or ""),
                description=str(queue_entity.description or ""),
                order=int(queue_entity.order or 0),
                queue_id=str(queue_entity.queue_id or ""),
                polling_interval_seconds=max(
                    int(queue_cfg.get("polling_interval_seconds") or 1),
                    1,
                ),
                max_messages=max(min(int(queue_cfg.get("max_messages") or 10), 10), 1),
                operations=[
                    _build_operation_snapshot(operation_entity)
                    for operation_entity in operations
                ],
            )
        )

    api_routes.sort(key=lambda item: (item.priority, item.order, item.id))
    queue_bindings.sort(key=lambda item: (item.order, item.id))

    return MockRuntimeServer(
        id=str(entity.id or ""),
        code=str(entity.code or ""),
        description=str(entity.description or ""),
        endpoint=endpoint,
        is_active=bool(entity.is_active),
        apis=api_routes,
        queues=queue_bindings,
    )
