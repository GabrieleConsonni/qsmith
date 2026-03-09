from typing import Any

from elaborations.services.scenarios.run_context import (
    RunContext,
    build_run_context_scope,
)
from elaborations.services.scenarios.run_context_resolver import resolve_dynamic_value
from mock_servers.models.runtime_models import MockApiRoute


def build_runtime_response_payload(
    route: MockApiRoute,
    *,
    run_context: RunContext,
    trigger_id: str,
) -> tuple[int, dict[str, Any], Any]:
    scope = build_run_context_scope(run_context)

    status_value = resolve_dynamic_value(route.response_status, scope)
    try:
        status_code = int(status_value if status_value is not None else 200)
    except (TypeError, ValueError):
        status_code = 200

    headers_value = resolve_dynamic_value(route.response_headers or {}, scope)
    headers = headers_value if isinstance(headers_value, dict) else {}

    body = resolve_dynamic_value(route.response_body, scope)
    if body is None:
        body = {"status": "ok"}

    # Keep backward compatibility with existing tests/UI by exposing trigger id.
    if isinstance(body, dict) and "trigger_id" not in body:
        body = dict(body)
        body["trigger_id"] = trigger_id

    return status_code, headers, body
