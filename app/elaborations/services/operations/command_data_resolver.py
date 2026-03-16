from elaborations.services.suite_runs.run_context import build_run_context_scope
from elaborations.services.suite_runs.run_context_resolver import resolve_dynamic_value


def resolve_command_input_data(source: str | None, data):
    if not source:
        return data
    resolved = resolve_dynamic_value(source, build_run_context_scope())
    return resolved


def coerce_rows(value) -> list[dict]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [value]
    return []
