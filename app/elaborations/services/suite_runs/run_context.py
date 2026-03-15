from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import Any, Iterable

from elaborations.models.enums.suite_item_kind import SuiteItemKind


@dataclass
class RunContext:
    run_id: str
    event: dict[str, Any] = field(default_factory=dict)
    global_vars: dict[str, Any] = field(default_factory=dict)
    local_vars: dict[str, Any] = field(default_factory=dict)
    last: dict[str, Any] = field(
        default_factory=lambda: {
            "item_id": "",
            "data": [],
        }
    )
    artifacts: dict[str, Any] = field(default_factory=dict)
    response_draft: dict[str, Any] = field(
        default_factory=lambda: {
            "status": None,
            "headers": {},
            "body": None,
        }
    )
    invocation_id: str | None = None
    current_item_kind: str = SuiteItemKind.HOOK.value
    current_hook_phase: str | None = None

    @property
    def vars(self) -> dict[str, Any]:
        return self.global_vars


_RUN_CONTEXT: ContextVar[RunContext | None] = ContextVar("run_context", default=None)


def create_run_context(
    *,
    run_id: str,
    event: dict[str, Any] | None = None,
    initial_vars: dict[str, Any] | None = None,
    invocation_id: str | None = None,
) -> RunContext:
    return RunContext(
        run_id=str(run_id or "").strip(),
        event=event if isinstance(event, dict) else {},
        global_vars=initial_vars if isinstance(initial_vars, dict) else {},
        invocation_id=str(invocation_id or "").strip() or None,
    )


def get_run_context() -> RunContext | None:
    return _RUN_CONTEXT.get()


@contextmanager
def bind_run_context(run_context: RunContext):
    token: Token = _RUN_CONTEXT.set(run_context)
    try:
        yield run_context
    finally:
        _RUN_CONTEXT.reset(token)


@contextmanager
def bind_suite_item_context(
    *,
    item_kind: str,
    hook_phase: str | None = None,
    local_vars: dict[str, Any] | None = None,
):
    context = get_run_context()
    if context is None:
        yield None
        return

    previous_kind = context.current_item_kind
    previous_hook_phase = context.current_hook_phase
    previous_local_vars = context.local_vars
    try:
        context.current_item_kind = str(item_kind or previous_kind).strip().lower()
        context.current_hook_phase = str(hook_phase or "").strip().lower() or None
        if local_vars is not None:
            context.local_vars = local_vars
        yield context
    finally:
        context.current_item_kind = previous_kind
        context.current_hook_phase = previous_hook_phase
        context.local_vars = previous_local_vars


def reset_local_context():
    context = get_run_context()
    if context is None:
        return
    context.local_vars = {}
    context.last = {"item_id": "", "data": []}


def set_context_last(item_id: str, data: Any):
    context = get_run_context()
    if context is None:
        return
    context.last = {
        "item_id": str(item_id or "").strip(),
        "data": data,
    }


def set_context_var(key: str, value: Any, scope: str = "auto"):
    context = get_run_context()
    if context is None:
        return
    normalized_key = str(key or "").strip()
    if not normalized_key:
        raise ValueError("Context variable key is required.")
    normalized_scope = str(scope or "auto").strip().lower()
    if normalized_scope == "auto":
        normalized_scope = (
            "local"
            if context.current_item_kind == SuiteItemKind.TEST.value
            else "global"
        )
    if normalized_scope == "global":
        if context.current_item_kind == SuiteItemKind.TEST.value:
            raise ValueError("Global context is immutable during test execution.")
        context.global_vars[normalized_key] = value
        return
    if normalized_scope != "local":
        raise ValueError(f"Unsupported context scope '{scope}'")
    context.local_vars[normalized_key] = value


def append_assert_artifact(artifact: dict[str, Any]):
    context = get_run_context()
    if context is None:
        return
    artifacts = context.artifacts.get("asserts")
    if not isinstance(artifacts, list):
        artifacts = []
        context.artifacts["asserts"] = artifacts
    artifacts.append(artifact)


def _normalize_target_path(path: str) -> str:
    normalized = str(path or "").strip()
    if not normalized:
        raise ValueError("Target path is required.")
    if normalized.startswith("$."):
        return normalized[2:]
    if normalized.startswith("$"):
        normalized = normalized[1:]
        if normalized.startswith("."):
            normalized = normalized[1:]
    return normalized


def _segment_tokens(segment: str) -> list[str]:
    source = str(segment or "").strip()
    if not source:
        return []
    result: list[str] = []
    buffer: list[str] = []
    index_mode = False
    for char in source:
        if char == "[":
            if buffer:
                result.append("".join(buffer))
                buffer = []
            index_mode = True
            continue
        if char == "]":
            token = "".join(buffer).strip()
            if token:
                result.append(token)
            buffer = []
            index_mode = False
            continue
        buffer.append(char)
    if buffer:
        result.append("".join(buffer) if not index_mode else "".join(buffer).strip())
    return [token for token in result if token]


def _path_tokens(path: str) -> list[str]:
    normalized = _normalize_target_path(path)
    parts = [part for part in normalized.split(".") if part]
    tokens: list[str] = []
    for part in parts:
        tokens.extend(_segment_tokens(part))
    return tokens


def extract_context_root(path: str) -> str | None:
    tokens = _path_tokens(path)
    if not tokens:
        return None
    root = str(tokens[0] or "").strip().lower()
    if root == "vars":
        return "global"
    if root in {"global", "local", "artifacts", "response"}:
        return root
    return None


def _target_from_root(context: RunContext, root: str):
    if root == "global":
        return context.global_vars
    if root == "local":
        return context.local_vars
    if root == "artifacts":
        return context.artifacts
    if root == "response":
        return context.response_draft
    raise ValueError(f"Unsupported context root '{root}'.")


def _to_index(token: str) -> int | None:
    raw = str(token or "").strip()
    if raw.isdigit():
        return int(raw)
    return None


def _ensure_list_size(items: list[Any], idx: int):
    while len(items) <= idx:
        items.append({})


def _assign_nested_value(target: Any, tokens: Iterable[str], value: Any):
    path_tokens = list(tokens)
    if not path_tokens:
        raise ValueError("Target path must include at least one segment.")

    current = target
    for idx, token in enumerate(path_tokens):
        is_last = idx == len(path_tokens) - 1
        list_index = _to_index(token)

        if list_index is not None:
            if not isinstance(current, list):
                raise ValueError("Target path expects a list segment.")
            _ensure_list_size(current, list_index)
            if is_last:
                current[list_index] = value
                return
            next_token = path_tokens[idx + 1]
            next_is_index = _to_index(next_token) is not None
            if current[list_index] is None:
                current[list_index] = [] if next_is_index else {}
            current = current[list_index]
            continue

        if not isinstance(current, dict):
            raise ValueError("Target path expects an object segment.")
        if is_last:
            current[token] = value
            return
        next_token = path_tokens[idx + 1]
        next_is_index = _to_index(next_token) is not None
        next_value = current.get(token)
        if next_value is None:
            current[token] = [] if next_is_index else {}
            next_value = current[token]
        current = next_value


def write_context_path(path: str, value: Any):
    context = get_run_context()
    if context is None:
        return

    root = extract_context_root(path)
    if root is None:
        raise ValueError(
            "Unsupported target path. Use one of $.global, $.local, $.artifacts, $.response."
        )

    if root == "global" and context.current_item_kind == SuiteItemKind.TEST.value:
        raise ValueError("Global context is immutable during test execution.")

    tokens = _path_tokens(path)
    root_token = tokens[0].lower()
    if root_token == "vars":
        root_token = "global"
    target_tokens = tokens[1:]
    target = _target_from_root(context, root_token)

    if not target_tokens:
        if not isinstance(value, dict):
            raise ValueError("Root assignment requires a JSON object value.")
        if root_token == "global":
            context.global_vars = value
        elif root_token == "local":
            context.local_vars = value
        elif root_token == "artifacts":
            context.artifacts = value
        else:
            context.response_draft = value
        return

    _assign_nested_value(target, target_tokens, value)


def set_response_status(value: Any):
    write_context_path("$.response.status", value)


def set_response_header(header_name: str, header_value: Any):
    context = get_run_context()
    if context is None:
        return
    normalized_header_name = str(header_name or "").strip()
    if not normalized_header_name:
        raise ValueError("Response header name is required.")
    headers = context.response_draft.get("headers")
    if not isinstance(headers, dict):
        headers = {}
        context.response_draft["headers"] = headers
    headers[normalized_header_name] = header_value


def set_response_body(value: Any):
    write_context_path("$.response.body", value)


def build_run_context_scope(run_context: RunContext | None = None) -> dict[str, Any]:
    context = run_context or get_run_context()
    if context is None:
        return {
            "event": {},
            "global": {},
            "local": {},
            "vars": {},
            "last": {},
            "artifacts": {},
            "response": {
                "status": None,
                "headers": {},
                "body": None,
            },
        }
    return {
        "event": context.event if isinstance(context.event, dict) else {},
        "global": context.global_vars if isinstance(context.global_vars, dict) else {},
        "local": context.local_vars if isinstance(context.local_vars, dict) else {},
        "vars": context.global_vars if isinstance(context.global_vars, dict) else {},
        "last": context.last if isinstance(context.last, dict) else {},
        "artifacts": context.artifacts if isinstance(context.artifacts, dict) else {},
        "response": (
            context.response_draft if isinstance(context.response_draft, dict) else {}
        ),
    }


def serialize_run_context(run_context: RunContext) -> dict[str, Any]:
    return {
        "run_id": str(run_context.run_id or "").strip(),
        "event": run_context.event if isinstance(run_context.event, dict) else {},
        "global": (
            run_context.global_vars if isinstance(run_context.global_vars, dict) else {}
        ),
        "local": run_context.local_vars if isinstance(run_context.local_vars, dict) else {},
        "vars": run_context.global_vars if isinstance(run_context.global_vars, dict) else {},
        "last": run_context.last if isinstance(run_context.last, dict) else {},
        "artifacts": (
            run_context.artifacts if isinstance(run_context.artifacts, dict) else {}
        ),
        "response": (
            run_context.response_draft
            if isinstance(run_context.response_draft, dict)
            else {"status": None, "headers": {}, "body": None}
        ),
        "invocation_id": str(run_context.invocation_id or "").strip() or None,
    }


def deserialize_run_context(payload: dict[str, Any] | None) -> RunContext:
    source = payload if isinstance(payload, dict) else {}
    context = create_run_context(
        run_id=str(source.get("run_id") or "").strip(),
        event=source.get("event") if isinstance(source.get("event"), dict) else {},
        initial_vars=(
            source.get("global")
            if isinstance(source.get("global"), dict)
            else (
                source.get("vars")
                if isinstance(source.get("vars"), dict)
                else {}
            )
        ),
        invocation_id=str(source.get("invocation_id") or "").strip() or None,
    )
    context.local_vars = source.get("local") if isinstance(source.get("local"), dict) else {}
    context.last = (
        source.get("last")
        if isinstance(source.get("last"), dict)
        else {"item_id": "", "data": []}
    )
    context.artifacts = (
        source.get("artifacts") if isinstance(source.get("artifacts"), dict) else {}
    )
    context.response_draft = (
        source.get("response")
        if isinstance(source.get("response"), dict)
        else {"status": None, "headers": {}, "body": None}
    )
    return context
