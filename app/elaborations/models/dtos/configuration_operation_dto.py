from enum import Enum

from pydantic import BaseModel, model_validator

from elaborations.models.enums.operation_type import OperationType


class ConfigurationOperationDto(BaseModel):
    operationType: str


def _normalize_target_path(value: object) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    if raw.startswith("$."):
        return raw
    if raw.startswith("$"):
        if raw.startswith("$."):
            return raw
        return f"$.{raw[1:].lstrip('.')}"
    return f"$.{raw.lstrip('.')}"


class DataConfigurationOperationDto(ConfigurationOperationDto):
    operationType: str = OperationType.DATA.value
    data: list[dict]
    target: str | None = None

    @model_validator(mode="after")
    def validate_target(self):
        self.target = _normalize_target_path(self.target)
        return self


class DataFromJsonArrayConfigurationOperationDto(ConfigurationOperationDto):
    operationType: str = OperationType.DATA_FROM_JSON_ARRAY.value
    json_array_id: str
    target: str | None = None

    @model_validator(mode="after")
    def validate_target(self):
        self.target = _normalize_target_path(self.target)
        return self


class DataFromDbConfigurationOperationDto(ConfigurationOperationDto):
    operationType: str = OperationType.DATA_FROM_DB.value
    dataset_id: str | None = None
    target: str | None = None

    @model_validator(mode="after")
    def validate_target(self):
        self.target = _normalize_target_path(self.target)
        return self


class DataFromQueueConfigurationOperationDto(ConfigurationOperationDto):
    operationType: str = OperationType.DATA_FROM_QUEUE.value
    queue_id: str
    retry: int = 3
    wait_time_seconds: int = 20
    max_messages: int = 1000
    target: str | None = None

    @model_validator(mode="after")
    def validate_target(self):
        self.target = _normalize_target_path(self.target)
        return self


class SleepConfigurationOperationDto(ConfigurationOperationDto):
    operationType: str = OperationType.SLEEP.value
    duration: int


class PublishConfigurationOperationDto(ConfigurationOperationDto):
    operationType: str = OperationType.PUBLISH.value
    queue_id: str
    template_id: str | None = None
    template_params: dict | None = None
    result_target: str | None = None

    @model_validator(mode="after")
    def validate_result_target(self):
        self.result_target = _normalize_target_path(self.result_target)
        return self


class SaveInternalDBConfigurationOperationDto(ConfigurationOperationDto):
    operationType: str = OperationType.SAVE_INTERNAL_DB.value
    table_name: str
    result_target: str | None = None

    @model_validator(mode="after")
    def validate_result_target(self):
        self.result_target = _normalize_target_path(self.result_target)
        return self


class SaveToExternalDBConfigurationOperationDto(ConfigurationOperationDto):
    operationType: str = OperationType.SAVE_EXTERNAL_DB.value
    connection_id: str | None = None
    table_name: str | None = None
    result_target: str | None = None

    @model_validator(mode="after")
    def validate_result_target(self):
        self.result_target = _normalize_target_path(self.result_target)
        return self


class RunSuiteConfigurationOperationDto(ConfigurationOperationDto):
    operationType: str = OperationType.RUN_SUITE.value
    suite_id: str | None = None
    suite_code: str | None = None
    init_vars: dict | None = None
    result_target: str | None = None

    @model_validator(mode="after")
    def validate_run_suite_configuration(self):
        suite_id = str(self.suite_id or "").strip()
        suite_code = str(self.suite_code or "").strip()
        if not suite_id and not suite_code:
            raise ValueError(
                "suite_id or suite_code is required for run-suite operation."
            )
        self.suite_id = suite_id or None
        self.suite_code = suite_code or None
        self.init_vars = self.init_vars if isinstance(self.init_vars, dict) else None
        self.result_target = _normalize_target_path(self.result_target)
        return self


RunScenarioConfigurationOperationDto = RunSuiteConfigurationOperationDto


class SetVarConfigurationOperationDto(ConfigurationOperationDto):
    operationType: str = OperationType.SET_VAR.value
    key: str
    value: object = None
    scope: str = "auto"

    @model_validator(mode="after")
    def validate_set_var_configuration(self):
        normalized_key = str(self.key or "").strip()
        if not normalized_key:
            raise ValueError("key is required for set-var operation.")
        self.key = normalized_key
        normalized_scope = str(self.scope or "auto").strip().lower()
        if normalized_scope not in {"auto", "local", "global"}:
            raise ValueError("scope must be one of: auto, local, global.")
        self.scope = normalized_scope
        return self


class SetResponseStatusConfigurationOperationDto(ConfigurationOperationDto):
    operationType: str = OperationType.SET_RESPONSE_STATUS.value
    status: object = 200


class SetResponseHeaderConfigurationOperationDto(ConfigurationOperationDto):
    operationType: str = OperationType.SET_RESPONSE_HEADER.value
    name: str
    value: object = None

    @model_validator(mode="after")
    def validate_name(self):
        normalized_name = str(self.name or "").strip()
        if not normalized_name:
            raise ValueError("name is required for set-response-header operation.")
        self.name = normalized_name
        return self


class SetResponseBodyConfigurationOperationDto(ConfigurationOperationDto):
    operationType: str = OperationType.SET_RESPONSE_BODY.value
    body: object = None


class BuildResponseFromTemplateConfigurationOperationDto(ConfigurationOperationDto):
    operationType: str = OperationType.BUILD_RESPONSE_FROM_TEMPLATE.value
    template: object | None = None
    status: object | None = None
    headers: dict | None = None


class AssertEvaluatedObjectType(str, Enum):
    JSON_DATA = "json-data"


class AssertType(str, Enum):
    NOT_EMPTY = "not-empty"
    EMPTY = "empty"
    SCHEMA_VALIDATION = "schema-validation"
    CONTAINS = "contains"
    JSON_ARRAY_EQUALS = "json-array-equals"
    EQUALS = "equals"


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
    actual: object | None = None
    expected: object | None = None
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

        if self.assert_type == AssertType.EQUALS.value and self.expected is None:
            raise ValueError("expected is required for equals assert.")

        return self


ConfigurationOperationTypes = (
    DataConfigurationOperationDto
    | DataFromJsonArrayConfigurationOperationDto
    | DataFromDbConfigurationOperationDto
    | DataFromQueueConfigurationOperationDto
    | SleepConfigurationOperationDto
    | PublishConfigurationOperationDto
    | SaveInternalDBConfigurationOperationDto
    | SaveToExternalDBConfigurationOperationDto
    | RunSuiteConfigurationOperationDto
    | SetVarConfigurationOperationDto
    | SetResponseStatusConfigurationOperationDto
    | SetResponseHeaderConfigurationOperationDto
    | SetResponseBodyConfigurationOperationDto
    | BuildResponseFromTemplateConfigurationOperationDto
    | AssertConfigurationOperationDto
)


def convert_to_config_operation_type(data: dict):
    operation_type = _normalize_token(
        _first_non_empty(data, "operationType", "operation_type", "type")
    )
    if operation_type == OperationType.DATA.value:
        return DataConfigurationOperationDto(
            data=_first_non_empty(data, "data") or [],
            target=_first_non_empty(data, "target", "target_path", "targetPath"),
        )
    if operation_type == OperationType.DATA_FROM_JSON_ARRAY.value:
        return DataFromJsonArrayConfigurationOperationDto(
            json_array_id=_first_non_empty(data, "json_array_id", "jsonArrayId"),
            target=_first_non_empty(data, "target", "target_path", "targetPath"),
        )
    if operation_type == OperationType.DATA_FROM_DB.value:
        return DataFromDbConfigurationOperationDto(
            dataset_id=_first_non_empty(data, "dataset_id", "datasetId", "data_source_id"),
            target=_first_non_empty(data, "target", "target_path", "targetPath"),
        )
    if operation_type == OperationType.DATA_FROM_QUEUE.value:
        return DataFromQueueConfigurationOperationDto(
            queue_id=_first_non_empty(data, "queue_id", "queueId"),
            retry=int(_first_non_empty(data, "retry") or 3),
            wait_time_seconds=int(
                _first_non_empty(data, "wait_time_seconds", "waitTimeSeconds") or 20
            ),
            max_messages=int(_first_non_empty(data, "max_messages", "maxMessages") or 1000),
            target=_first_non_empty(data, "target", "target_path", "targetPath"),
        )
    if operation_type == OperationType.SLEEP.value:
        return SleepConfigurationOperationDto(
            duration=int(_first_non_empty(data, "duration") or 0)
        )
    if operation_type == OperationType.PUBLISH.value:
        return PublishConfigurationOperationDto(
            queue_id=_first_non_empty(data, "queue_id", "queueId"),
            template_id=_first_non_empty(data, "template_id", "templateId"),
            template_params=_first_non_empty(data, "template_params", "templateParams"),
            result_target=_first_non_empty(
                data, "result_target", "resultTarget", "outputTarget"
            ),
        )
    if operation_type == OperationType.SAVE_INTERNAL_DB.value:
        return SaveInternalDBConfigurationOperationDto(
            table_name=_first_non_empty(data, "table_name", "tableName"),
            result_target=_first_non_empty(
                data, "result_target", "resultTarget", "outputTarget"
            ),
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
            table_name=_first_non_empty(data, "table_name", "tableName"),
            result_target=_first_non_empty(
                data, "result_target", "resultTarget", "outputTarget"
            ),
        )
    if operation_type in {OperationType.RUN_SUITE.value, "run-scenario"}:
        return RunSuiteConfigurationOperationDto(
            suite_id=_first_non_empty(data, "suite_id", "suiteId", "scenario_id", "scenarioId"),
            suite_code=_first_non_empty(
                data,
                "suite_code",
                "suiteCode",
                "scenario_code",
                "scenarioCode",
            ),
            init_vars=_first_non_empty(data, "init_vars", "initVars"),
            result_target=_first_non_empty(
                data, "result_target", "resultTarget", "outputTarget"
            ),
        )
    if operation_type == OperationType.SET_VAR.value:
        return SetVarConfigurationOperationDto(
            key=_first_non_empty(data, "key", "var_key", "varKey"),
            value=_first_non_empty(data, "value"),
            scope=_first_non_empty(data, "scope", "target_scope", "targetScope") or "auto",
        )
    if operation_type == OperationType.SET_RESPONSE_STATUS.value:
        return SetResponseStatusConfigurationOperationDto(
            status=_first_non_empty(
                data, "status", "response_status", "responseStatus"
            ),
        )
    if operation_type == OperationType.SET_RESPONSE_HEADER.value:
        return SetResponseHeaderConfigurationOperationDto(
            name=_first_non_empty(data, "name", "header", "header_name", "headerName"),
            value=_first_non_empty(data, "value", "header_value", "headerValue"),
        )
    if operation_type == OperationType.SET_RESPONSE_BODY.value:
        return SetResponseBodyConfigurationOperationDto(
            body=_first_non_empty(data, "body", "value", "response_body", "responseBody")
        )
    if operation_type == OperationType.BUILD_RESPONSE_FROM_TEMPLATE.value:
        return BuildResponseFromTemplateConfigurationOperationDto(
            template=_first_non_empty(data, "template", "body", "value"),
            status=_first_non_empty(data, "status", "response_status", "responseStatus"),
            headers=_first_non_empty(data, "headers", "response_headers", "responseHeaders"),
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
            actual=_first_non_empty(data, "actual"),
            expected=_first_non_empty(data, "expected"),
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
