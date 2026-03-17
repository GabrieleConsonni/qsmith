from data_sources.services.dataset_query_service import DatasetQueryService
from elaborations.models.dtos.configuration_command_dto import ConstantSourceType
from elaborations.services.constants.command_constant_definition_registry import (
    resolve_definition_path,
)
from elaborations.services.suite_runs.run_context import (
    build_run_context_scope,
    write_context_path,
)
from elaborations.services.suite_runs.run_context_resolver import resolve_dynamic_value


def resolve_command_input_data(source: str | None, data):
    if not source:
        return data
    resolved = resolve_dynamic_value(source, build_run_context_scope())
    return resolved


def _resolve_dataset_rows(session, definition, resolved_value):
    dataset_id = str(resolved_value or "").strip() if isinstance(resolved_value, str) else ""
    if not dataset_id:
        raise ValueError(
            f"Dataset constant '{definition.name}' must resolve to a dataset id string."
        )
    dataset = DatasetQueryService.get_dataset_or_raise_for_runtime(session, dataset_id)
    return DatasetQueryService.load_rows_for_runtime(dataset)


def resolve_definition_input_data(session, definition_id: str | None, data):
    if not definition_id:
        return data
    definition, path = resolve_definition_path(session, definition_id)
    resolved = resolve_dynamic_value(path, build_run_context_scope())
    if resolved == path:
        return None
    if str(getattr(definition, "value_type", "") or "").strip() == ConstantSourceType.DATASET.value:
        return _resolve_dataset_rows(session, definition, resolved)
    return resolved


def write_result_constant(session, result_constant, value):
    if result_constant is None:
        return
    _definition, path = resolve_definition_path(session, result_constant.definitionId)
    write_context_path(path, value)


def coerce_rows(value) -> list[dict]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [value]
    return []
