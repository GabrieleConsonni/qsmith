from dataclasses import dataclass, field
from typing import Any


@dataclass
class MockOperationSnapshot:
    id: str
    description: str
    operation_type: str
    configuration_json: dict[str, Any]
    order: int


@dataclass
class MockApiRoute:
    id: str
    description: str
    order: int
    method: str
    path: str
    params: dict[str, Any]
    headers: dict[str, Any]
    body: Any
    body_match: str
    priority: int
    response_status: Any
    response_headers: dict[str, Any]
    response_body: Any
    operations: list[MockOperationSnapshot] = field(default_factory=list)
    pre_response_operations: list[MockOperationSnapshot] = field(default_factory=list)
    response_operations: list[MockOperationSnapshot] = field(default_factory=list)
    post_response_operations: list[MockOperationSnapshot] = field(default_factory=list)


@dataclass
class MockQueueBinding:
    id: str
    description: str
    order: int
    queue_id: str
    polling_interval_seconds: int
    max_messages: int
    operations: list[MockOperationSnapshot] = field(default_factory=list)


@dataclass
class MockRuntimeServer:
    id: str
    description: str
    endpoint: str
    is_active: bool
    apis: list[MockApiRoute] = field(default_factory=list)
    queues: list[MockQueueBinding] = field(default_factory=list)
