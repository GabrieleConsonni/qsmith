from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RunContext:
    run_id: str
    event: dict[str, Any] = field(default_factory=dict)
    vars: dict[str, Any] = field(default_factory=dict)
    last: dict[str, Any] = field(
        default_factory=lambda: {
            "step_code": "",
            "data": [],
        }
    )
    artifacts: dict[str, Any] = field(default_factory=dict)
    invocation_id: str | None = None


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
        vars=initial_vars if isinstance(initial_vars, dict) else {},
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


def set_context_last(step_code: str, data: Any):
    context = get_run_context()
    if context is None:
        return
    context.last = {
        "step_code": str(step_code or "").strip(),
        "data": data,
    }


def set_context_var(key: str, value: Any):
    context = get_run_context()
    if context is None:
        return
    normalized_key = str(key or "").strip()
    if not normalized_key:
        raise ValueError("Context variable key is required.")
    context.vars[normalized_key] = value


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
            "vars": {},
            "last": {},
            "artifacts": {},
        }
    return {
        "event": context.event if isinstance(context.event, dict) else {},
        "vars": context.vars if isinstance(context.vars, dict) else {},
        "last": context.last if isinstance(context.last, dict) else {},
        "artifacts": context.artifacts if isinstance(context.artifacts, dict) else {},
    }


def serialize_run_context(run_context: RunContext) -> dict[str, Any]:
    return {
        "run_id": str(run_context.run_id or "").strip(),
        "event": run_context.event if isinstance(run_context.event, dict) else {},
        "vars": run_context.vars if isinstance(run_context.vars, dict) else {},
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
        initial_vars=source.get("vars") if isinstance(source.get("vars"), dict) else {},
        invocation_id=str(source.get("invocation_id") or "").strip() or None,
    )
    context.last = source.get("last") if isinstance(source.get("last"), dict) else {"step_code": "", "data": []}
    context.artifacts = (
        source.get("artifacts")
        if isinstance(source.get("artifacts"), dict)
        else {}
    )
    return context
