from enum import Enum

from pydantic import BaseModel, model_validator

from elaborations.models.enums.operation_type import OperationType


class ConfigurationOperationDto(BaseModel):
    operationType: str


class PublishConfigurationOperationDto(ConfigurationOperationDto):
    operationType: str = OperationType.PUBLISH.value
    queue_id: str
    template_id: str | None = None
    template_params: dict | None = None


class SaveInternalDBConfigurationOperationDto(ConfigurationOperationDto):
    operationType: str = OperationType.SAVE_INTERNAL_DB.value
    table_name: str


class SaveToExternalDBConfigurationOperationDto(ConfigurationOperationDto):
    operationType: str = OperationType.SAVE_EXTERNAL_DB.value
    connection_id: str | None = None
    table_name: str | None = None


class RunScenarioConfigurationOperationDto(ConfigurationOperationDto):
    operationType: str = OperationType.RUN_SCENARIO.value
    scenario_id: str

    @model_validator(mode="after")
    def validate_run_scenario_configuration(self):
        scenario_id = str(self.scenario_id or "").strip()
        if not scenario_id:
            raise ValueError("scenario_id is required for run-scenario operation.")
        self.scenario_id = scenario_id
        return self


class AssertEvaluatedObjectType(str, Enum):
    JSON_DATA = "json-data"


class AssertType(str, Enum):
    NOT_EMPTY = "not-empty"
    EMPTY = "empty"
    SCHEMA_VALIDATION = "schema-validation"
    CONTAINS = "contains"
    JSON_ARRAY_EQUALS = "json-array-equals"


def _normalize_token(value: object) -> str:
    return str(value or "").strip().replace("_", "-").lower()


def _first_non_empty(data: dict, *keys: str):
    for key in keys:
        value = data.get(key)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _normalize_compare_keys(value: object) -> list[str]:
    if isinstance(value, str):
        raw_items = value.replace(";", ",").replace("\n", ",").split(",")
        return [item.strip() for item in raw_items if item and item.strip()]
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            normalized = str(item or "").strip()
            if normalized:
                result.append(normalized)
        return result
    return []


class AssertConfigurationOperationDto(ConfigurationOperationDto):
    operationType: str = OperationType.ASSERT.value
    error_message: str | None = None
    evaluated_object_type: str = AssertEvaluatedObjectType.JSON_DATA.value
    assert_type: str
    expected_json_array_id: str | None = None
    compare_keys: list[str] | None = None
    json_schema: dict | None = None

    @model_validator(mode="after")
    def validate_assert_configuration(self):
        self.assert_type = _normalize_token(self.assert_type)
        self.evaluated_object_type = _normalize_token(self.evaluated_object_type)

        supported_assert_types = {assert_type.value for assert_type in AssertType}
        if self.assert_type not in supported_assert_types:
            raise ValueError(
                f"Unsupported assert_type: {self.assert_type}. "
                f"Supported types: {sorted(supported_assert_types)}"
            )

        supported_object_types = {
            object_type.value for object_type in AssertEvaluatedObjectType
        }
        if self.evaluated_object_type not in supported_object_types:
            raise ValueError(
                f"Unsupported evaluated_object_type: {self.evaluated_object_type}. "
                f"Supported types: {sorted(supported_object_types)}"
            )

        self.expected_json_array_id = str(self.expected_json_array_id or "").strip() or None
        normalized_compare_keys = _normalize_compare_keys(self.compare_keys)
        self.compare_keys = normalized_compare_keys or None

        if self.assert_type in {
            AssertType.CONTAINS.value,
            AssertType.JSON_ARRAY_EQUALS.value,
        }:
            if not self.expected_json_array_id:
                raise ValueError(
                    "expected_json_array_id is required for contains/json-array-equals assert."
                )
            if not self.compare_keys:
                raise ValueError(
                    "compare_keys is required for contains/json-array-equals assert."
                )

        if self.assert_type == AssertType.SCHEMA_VALIDATION.value:
            if not isinstance(self.json_schema, dict):
                raise ValueError("json_schema is required for schema-validation assert.")

        return self


ConfigurationOperationTypes = (
    PublishConfigurationOperationDto
    | SaveInternalDBConfigurationOperationDto
    | SaveToExternalDBConfigurationOperationDto
    | RunScenarioConfigurationOperationDto
    | AssertConfigurationOperationDto
)


def convert_to_config_operation_type(data: dict):
    operation_type = _normalize_token(_first_non_empty(data, "operationType", "operation_type"))
    if operation_type == OperationType.PUBLISH.value:
        return PublishConfigurationOperationDto(
            queue_id=_first_non_empty(data, "queue_id", "queueId"),
            template_id=_first_non_empty(data, "template_id", "templateId"),
            template_params=_first_non_empty(data, "template_params", "templateParams"),
        )
    if operation_type == OperationType.SAVE_INTERNAL_DB.value:
        return SaveInternalDBConfigurationOperationDto(
            table_name=_first_non_empty(data, "table_name", "tableName")
        )
    if operation_type == OperationType.SAVE_EXTERNAL_DB.value:
        return SaveToExternalDBConfigurationOperationDto(
            connection_id=_first_non_empty(
                data,
                "connection_id",
                "connectionId",
                "dataset_id",
                "datasetId",
            ),
            table_name=_first_non_empty(data, "table_name", "tableName")
        )
    if operation_type == OperationType.RUN_SCENARIO.value:
        return RunScenarioConfigurationOperationDto(
            scenario_id=_first_non_empty(data, "scenario_id", "scenarioId"),
        )
    if operation_type == OperationType.ASSERT.value:
        return AssertConfigurationOperationDto(
            error_message=_first_non_empty(data, "error_message", "errorMessage"),
            evaluated_object_type=(
                _normalize_token(
                    _first_non_empty(
                        data,
                        "evaluated_object_type",
                        "evaluetedObjectType",
                        "evaluatedObjectType",
                    )
                )
                or AssertEvaluatedObjectType.JSON_DATA.value
            ),
            assert_type=_normalize_token(_first_non_empty(data, "assert_type", "assertType")),
            expected_json_array_id=_first_non_empty(
                data,
                "expected_json_array_id",
                "expectedJsonArrayId",
                "json_array_id",
            ),
            compare_keys=_normalize_compare_keys(
                _first_non_empty(data, "compare_keys", "compareKeys")
            ),
            json_schema=_first_non_empty(data, "json_schema", "jsonSchema"),
        )
    raise ValueError(f"Unsupported operation type: {operation_type}")
