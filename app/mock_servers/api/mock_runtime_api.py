import json

from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import JSONResponse

from mock_servers.services.runtime.mock_runtime_dispatcher import (
    dispatch_mock_runtime_request,
)

router = APIRouter()

_RUNTIME_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]


def _query_params_as_dict(request: Request) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in request.query_params.multi_items():
        if key not in result:
            result[key] = value
    return result


async def _dispatch_runtime_request(
    request: Request,
    background_tasks: BackgroundTasks,
    server_endpoint: str,
    path: str,
):
    body_raw = ""
    body_json = None
    raw_payload = await request.body()
    if raw_payload:
        body_raw = raw_payload.decode("utf-8")
        try:
            body_json = json.loads(body_raw)
        except json.JSONDecodeError:
            body_json = None

    dispatch_result = dispatch_mock_runtime_request(
        server_endpoint=server_endpoint,
        method=request.method,
        path=path or "/",
        query_params=_query_params_as_dict(request),
        headers=dict(request.headers),
        body_raw=body_raw,
        body_json=body_json,
        background_tasks=background_tasks,
    )
    if not dispatch_result:
        return JSONResponse(
            status_code=404,
            content={"detail": "Mock route not found or inactive."},
        )
    status_code, headers, response_body = dispatch_result
    return JSONResponse(
        status_code=status_code,
        headers=headers,
        content=response_body,
    )


@router.api_route("/mock/{server_endpoint}", methods=_RUNTIME_METHODS)
async def dispatch_mock_runtime_root_api(
    request: Request,
    background_tasks: BackgroundTasks,
    server_endpoint: str,
):
    return await _dispatch_runtime_request(
        request=request,
        background_tasks=background_tasks,
        server_endpoint=server_endpoint,
        path="/",
    )


@router.api_route("/mock/{server_endpoint}/{path:path}", methods=_RUNTIME_METHODS)
async def dispatch_mock_runtime_api(
    request: Request,
    background_tasks: BackgroundTasks,
    server_endpoint: str,
    path: str,
):
    return await _dispatch_runtime_request(
        request=request,
        background_tasks=background_tasks,
        server_endpoint=server_endpoint,
        path=path,
    )
