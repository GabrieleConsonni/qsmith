from contextlib import contextmanager
from contextvars import ContextVar, Token


_EXECUTION_ID: ContextVar[str | None] = ContextVar("execution_id", default=None)
_SCENARIO_ID: ContextVar[str | None] = ContextVar("scenario_id", default=None)
_SCENARIO_STEP_ID: ContextVar[str | None] = ContextVar("scenario_step_id", default=None)
_SCENARIO_EXECUTION_ID: ContextVar[str | None] = ContextVar("scenario_execution_id", default=None)
_SCENARIO_STEP_EXECUTION_ID: ContextVar[str | None] = ContextVar("scenario_step_execution_id", default=None)


def get_execution_id() -> str | None:
    return _EXECUTION_ID.get()


def get_scenario_id() -> str | None:
    return _SCENARIO_ID.get()


def get_scenario_step_id() -> str | None:
    return _SCENARIO_STEP_ID.get()


def get_scenario_execution_id() -> str | None:
    return _SCENARIO_EXECUTION_ID.get()


def get_scenario_step_execution_id() -> str | None:
    return _SCENARIO_STEP_EXECUTION_ID.get()


@contextmanager
def bind_execution_context(
    *,
    execution_id: str | None = None,
    scenario_id: str | None = None,
    scenario_step_id: str | None = None,
    scenario_execution_id: str | None = None,
    scenario_step_execution_id: str | None = None,
):
    tokens: list[tuple[ContextVar, Token]] = []
    try:
        if execution_id is not None:
            tokens.append((_EXECUTION_ID, _EXECUTION_ID.set(execution_id)))
        if scenario_id is not None:
            tokens.append((_SCENARIO_ID, _SCENARIO_ID.set(scenario_id)))
        if scenario_step_id is not None:
            tokens.append((_SCENARIO_STEP_ID, _SCENARIO_STEP_ID.set(scenario_step_id)))
        if scenario_execution_id is not None:
            tokens.append((_SCENARIO_EXECUTION_ID, _SCENARIO_EXECUTION_ID.set(scenario_execution_id)))
        if scenario_step_execution_id is not None:
            tokens.append(
                (_SCENARIO_STEP_EXECUTION_ID, _SCENARIO_STEP_EXECUTION_ID.set(scenario_step_execution_id))
            )
        yield
    finally:
        for context_var, token in reversed(tokens):
            context_var.reset(token)
