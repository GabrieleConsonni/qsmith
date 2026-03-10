from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import Any

from elaborations.models.enums.suite_item_kind import SuiteItemKind


@dataclass
class RunContext:
    run_id: str
    event: dict[str, Any] = field(default_factory=dict)
    global_vars: dict[str, Any] = field(default_factory=dict)
    local_vars: dict[str, Any] = field(default_factory=dict)
    last: dict[str, Any] = field(
        default_factory=lambda: {
            "item_code": "",
            "data": [],
        }
    )
    artifacts: dict[str, Any] = field(default_factory=dict)
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
    context.last = {"item_code": "", "data": []}


def set_context_last(item_code: str, data: Any):
    context = get_run_context()
    if context is None:
        return
    context.last = {
        "item_code": str(item_code or "").strip(),
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
        }
    return {
        "event": context.event if isinstance(context.event, dict) else {},
        "global": context.global_vars if isinstance(context.global_vars, dict) else {},
        "local": context.local_vars if isinstance(context.local_vars, dict) else {},
        "vars": context.global_vars if isinstance(context.global_vars, dict) else {},
        "last": context.last if isinstance(context.last, dict) else {},
        "artifacts": context.artifacts if isinstance(context.artifacts, dict) else {},
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
    context.last = source.get("last") if isinstance(source.get("last"), dict) else {"item_code": "", "data": []}
    context.artifacts = (
        source.get("artifacts")
        if isinstance(source.get("artifacts"), dict)
        else {}
    )
    return context
