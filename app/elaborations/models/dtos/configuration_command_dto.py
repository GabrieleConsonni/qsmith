from enum import Enum

from pydantic import BaseModel, Field, model_validator


class CommandType(str, Enum):
    CONTEXT = "context"
    ACTION = "action"
    ASSERT = "assert"


class CommandCode(str, Enum):
    INIT_CONSTANT = "initConstant"
    DELETE_CONSTANT = "deleteConstant"
    SLEEP = "sleep"
    SEND_MESSAGE_QUEUE = "sendMessageQueue"
    SAVE_TABLE = "saveTable"
    DROP_TABLE = "dropTable"
    CLEAN_TABLE = "cleanTable"
    EXPORT_DATASET = "exportDataset"
    DROP_DATASET = "dropDataset"
    CLEAN_DATASET = "cleanDataset"
    RUN_SUITE = "runSuite"
    JSON_EQUALS = "jsonEquals"
    JSON_EMPTY = "jsonEmpty"
    JSON_NOT_EMPTY = "jsonNotEmpty"
    JSON_CONTAINS = "jsonContains"
    JSON_ARRAY_EQUALS = "jsonArrayEquals"
    JSON_ARRAY_EMPTY = "jsonArrayEmpty"
    JSON_ARRAY_NOT_EMPTY = "jsonArrayNotEmpty"
    JSON_ARRAY_CONTAINS = "jsonArrayContains"


class ConstantContext(str, Enum):
    RUN_ENVELOPE = "runEnvelope"
    GLOBAL = "global"
    LOCAL = "local"
    RESULT = "result"


class ConstantSourceType(str, Enum):
    RAW = "raw"
    JSON = "json"
    JSON_ARRAY = "jsonArray"
    DATASET = "dataset"
    SQS_QUEUE = "sqsQueue"


class AssertEvaluatedObjectType(str, Enum):
    JSON_DATA = "json-data"


class AssertType(str, Enum):
    NOT_EMPTY = "not-empty"
    EMPTY = "empty"
    SCHEMA_VALIDATION = "schema-validation"
    CONTAINS = "contains"
    JSON_ARRAY_EQUALS = "json-array-equals"
    JSON_ARRAY_CONTAINS = "json-array-contains"
    EQUALS = "equals"


class ConstantRefDto(BaseModel):
    definitionId: str

    @model_validator(mode="after")
    def validate_definition_id(self):
        self.definitionId = _normalize_token(self.definitionId)
        if not self.definitionId:
            raise ValueError("definitionId is required.")
        return self


class ResultConstantDto(BaseModel):
    definitionId: str
    name: str
    valueType: str = ConstantSourceType.JSON.value

    @model_validator(mode="after")
    def validate_result_constant(self):
        self.definitionId = _normalize_token(self.definitionId)
        self.name = _normalize_token(self.name)
        self.valueType = _normalize_token(self.valueType) or ConstantSourceType.JSON.value
        if not self.definitionId:
            raise ValueError("resultConstant.definitionId is required.")
        if not self.name:
            raise ValueError("resultConstant.name is required.")
        if self.valueType not in {item.value for item in ConstantSourceType}:
            raise ValueError("Unsupported resultConstant.valueType.")
        return self


def _normalize_token(value: object) -> str:
    return str(value or "").strip()


def _normalize_path_token(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    return raw.replace("_", "-")


def _first_non_empty(data: dict, *keys: str):
    for key in keys:
        value = data.get(key)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _normalize_target_path(value: object) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    if raw.startswith("$."):
        return raw
    if raw.startswith("$"):
        return f"$.{raw[1:].lstrip('.')}"
    return f"$.{raw.lstrip('.')}"


def _normalize_definition_id(value: object) -> str:
    return _normalize_token(value)


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


def _coerce_constant_ref(value: object) -> ConstantRefDto | None:
    if isinstance(value, ConstantRefDto):
        return value
    if isinstance(value, dict):
        definition_id = _first_non_empty(value, "definitionId", "definition_id")
        if definition_id:
            return ConstantRefDto(definitionId=definition_id)
    return None


def _coerce_result_constant(value: object) -> ResultConstantDto | None:
    if isinstance(value, ResultConstantDto):
        return value
    if isinstance(value, dict):
        definition_id = _first_non_empty(value, "definitionId", "definition_id")
        name = _first_non_empty(value, "name")
        value_type = _first_non_empty(value, "valueType", "value_type")
        if definition_id or name:
            return ResultConstantDto(
                definitionId=definition_id or "",
                name=name or "",
                valueType=value_type or ConstantSourceType.JSON.value,
            )
    return None


def _normalize_command_type(value: object) -> str:
    normalized = _normalize_token(value).lower()
    if normalized in {item.value for item in CommandType}:
        return normalized
    return normalized


def _normalize_command_code(value: object) -> str:
    raw = _normalize_token(value)
    if not raw:
        return ""
    legacy = raw.replace("_", "-").lower()
    legacy_mapping = {
        "data": CommandCode.INIT_CONSTANT.value,
        "data-from-json-array": CommandCode.INIT_CONSTANT.value,
        "data-from-db": CommandCode.INIT_CONSTANT.value,
        "data-from-queue": CommandCode.INIT_CONSTANT.value,
        "publish": CommandCode.SEND_MESSAGE_QUEUE.value,
        "save-internal-db": CommandCode.SAVE_TABLE.value,
        "save-external-db": CommandCode.EXPORT_DATASET.value,
        "run-suite": CommandCode.RUN_SUITE.value,
        "set-var": CommandCode.INIT_CONSTANT.value,
    }
    return legacy_mapping.get(legacy, raw)


def _derive_assert_command_code(data: dict) -> str:
    assert_type = _normalize_token(_first_non_empty(data, "assert_type", "assertType")).replace("_", "-").lower()
    if assert_type == "equals":
        return CommandCode.JSON_EQUALS.value
    if assert_type == "empty":
        expected_json_array_id = _first_non_empty(
            data,
            "expected_json_array_id",
            "expectedJsonArrayId",
            "json_array_id",
        )
        return (
            CommandCode.JSON_ARRAY_EMPTY.value
            if expected_json_array_id
            else CommandCode.JSON_EMPTY.value
        )
    if assert_type == "not-empty":
        expected_json_array_id = _first_non_empty(
            data,
            "expected_json_array_id",
            "expectedJsonArrayId",
            "json_array_id",
        )
        return (
            CommandCode.JSON_ARRAY_NOT_EMPTY.value
            if expected_json_array_id
            else CommandCode.JSON_NOT_EMPTY.value
        )
    if assert_type == "contains":
        expected_json_array_id = _first_non_empty(
            data,
            "expected_json_array_id",
            "expectedJsonArrayId",
            "json_array_id",
        )
        return (
            CommandCode.JSON_ARRAY_CONTAINS.value
            if expected_json_array_id
            else CommandCode.JSON_CONTAINS.value
        )
    if assert_type == "json-array-equals":
        return CommandCode.JSON_ARRAY_EQUALS.value
    return CommandCode.JSON_EQUALS.value


class ConfigurationCommandDto(BaseModel):
    commandCode: str
    commandType: str

    @model_validator(mode="after")
    def validate_command_keys(self):
        self.commandCode = _normalize_command_code(self.commandCode)
        self.commandType = _normalize_command_type(self.commandType)
        if not self.commandCode:
            raise ValueError("commandCode is required.")
        if self.commandType not in {item.value for item in CommandType}:
            raise ValueError("commandType must be one of: context, action, assert.")
        return self


class InitConstantConfigurationCommandDto(ConfigurationCommandDto):
    commandCode: str = CommandCode.INIT_CONSTANT.value
    commandType: str = CommandType.CONTEXT.value
    definitionId: str | None = None
    name: str | None = None
    context: str | None = None
    sourceType: str | None = None
    value: object = None
    data: object = None
    json_array_id: str | None = None
    dataset_id: str | None = None
    queue_id: str | None = None
    retry: int = 3
    wait_time_seconds: int = 20
    max_messages: int = 1000
    target: str | None = None
    key: str | None = None
    scope: str | None = None

    @model_validator(mode="after")
    def validate_configuration(self):
        self.definitionId = _normalize_definition_id(self.definitionId)
        if not self.definitionId:
            raise ValueError("definitionId is required for initConstant.")
        self.target = _normalize_target_path(self.target)
        if self.target:
            target_tokens = [token for token in self.target.split(".") if token]
            if len(target_tokens) >= 3:
                self.context = self.context or target_tokens[1]
                self.name = self.name or target_tokens[-1]
        self.name = _normalize_token(self.name or self.key)
        if not self.name:
            raise ValueError("name is required for initConstant.")

        normalized_context = _normalize_token(self.context or self.scope or ConstantContext.LOCAL.value)
        normalized_context = {
            "run": ConstantContext.RUN_ENVELOPE.value,
            "vars": ConstantContext.GLOBAL.value,
            "auto": ConstantContext.LOCAL.value,
        }.get(normalized_context, normalized_context)
        if normalized_context not in {item.value for item in ConstantContext}:
            raise ValueError("context must be one of: runEnvelope, global, local, result.")
        self.context = normalized_context

        detected_source_type = _normalize_token(self.sourceType)
        if not detected_source_type:
            if self.queue_id:
                detected_source_type = ConstantSourceType.SQS_QUEUE.value
            elif self.dataset_id:
                detected_source_type = ConstantSourceType.DATASET.value
            elif self.json_array_id:
                detected_source_type = ConstantSourceType.JSON_ARRAY.value
            elif self.data is not None:
                self.value = self.data
                detected_source_type = (
                    ConstantSourceType.JSON.value
                    if isinstance(self.data, (dict, list))
                    else ConstantSourceType.RAW.value
                )
            else:
                detected_source_type = (
                    ConstantSourceType.JSON.value
                    if isinstance(self.value, (dict, list))
                    else ConstantSourceType.RAW.value
                )
        if detected_source_type not in {item.value for item in ConstantSourceType}:
            raise ValueError("Unsupported sourceType for initConstant.")
        self.sourceType = detected_source_type

        return self


class DeleteConstantConfigurationCommandDto(ConfigurationCommandDto):
    commandCode: str = CommandCode.DELETE_CONSTANT.value
    commandType: str = CommandType.CONTEXT.value
    targetConstantRef: ConstantRefDto | None = None

    @model_validator(mode="after")
    def validate_configuration(self):
        self.targetConstantRef = _coerce_constant_ref(self.targetConstantRef)
        if self.targetConstantRef is None:
            raise ValueError("targetConstantRef is required for deleteConstant.")
        return self


class SleepConfigurationCommandDto(ConfigurationCommandDto):
    commandCode: str = CommandCode.SLEEP.value
    commandType: str = CommandType.ACTION.value
    duration: int


class SendMessageQueueConfigurationCommandDto(ConfigurationCommandDto):
    commandCode: str = CommandCode.SEND_MESSAGE_QUEUE.value
    commandType: str = CommandType.ACTION.value
    queue_id: str
    sourceConstantRef: ConstantRefDto | None = None
    template_id: str | None = None
    template_params: dict | None = None
    resultConstant: ResultConstantDto | None = None

    @model_validator(mode="after")
    def validate_configuration(self):
        self.sourceConstantRef = _coerce_constant_ref(self.sourceConstantRef)
        self.resultConstant = _coerce_result_constant(self.resultConstant)
        if self.sourceConstantRef is None:
            raise ValueError("sourceConstantRef is required for sendMessageQueue.")
        return self


class SaveTableConfigurationCommandDto(ConfigurationCommandDto):
    commandCode: str = CommandCode.SAVE_TABLE.value
    commandType: str = CommandType.ACTION.value
    table_name: str
    sourceConstantRef: ConstantRefDto | None = None
    resultConstant: ResultConstantDto | None = None

    @model_validator(mode="after")
    def validate_configuration(self):
        self.sourceConstantRef = _coerce_constant_ref(self.sourceConstantRef)
        self.resultConstant = _coerce_result_constant(self.resultConstant)
        if self.sourceConstantRef is None:
            raise ValueError("sourceConstantRef is required for saveTable.")
        return self


class DropTableConfigurationCommandDto(ConfigurationCommandDto):
    commandCode: str = CommandCode.DROP_TABLE.value
    commandType: str = CommandType.ACTION.value
    table_name: str


class CleanTableConfigurationCommandDto(ConfigurationCommandDto):
    commandCode: str = CommandCode.CLEAN_TABLE.value
    commandType: str = CommandType.ACTION.value
    table_name: str


class ExportDatasetConfigurationCommandDto(ConfigurationCommandDto):
    commandCode: str = CommandCode.EXPORT_DATASET.value
    commandType: str = CommandType.ACTION.value
    connection_id: str | None = None
    table_name: str | None = None
    sourceConstantRef: ConstantRefDto | None = None
    mode: str = "append"
    mapping_keys: list[str] | None = None
    dataset_description: str | None = None
    dataset_id: str | None = None
    resultConstant: ResultConstantDto | None = None

    @model_validator(mode="after")
    def validate_configuration(self):
        self.sourceConstantRef = _coerce_constant_ref(self.sourceConstantRef)
        self.resultConstant = _coerce_result_constant(self.resultConstant)
        if self.sourceConstantRef is None:
            raise ValueError("sourceConstantRef is required for exportDataset.")
        normalized_mode = _normalize_token(self.mode).replace("_", "-").lower() or "append"
        if normalized_mode not in {"append", "drop-create", "insert-update"}:
            raise ValueError("mode must be one of: append, drop-create, insert-update.")
        self.mode = normalized_mode
        keys = _normalize_compare_keys(self.mapping_keys)
        self.mapping_keys = keys or None
        return self


class DropDatasetConfigurationCommandDto(ConfigurationCommandDto):
    commandCode: str = CommandCode.DROP_DATASET.value
    commandType: str = CommandType.ACTION.value
    dataset_id: str


class CleanDatasetConfigurationCommandDto(ConfigurationCommandDto):
    commandCode: str = CommandCode.CLEAN_DATASET.value
    commandType: str = CommandType.ACTION.value
    dataset_id: str


class RunSuiteConfigurationCommandDto(ConfigurationCommandDto):
    commandCode: str = CommandCode.RUN_SUITE.value
    commandType: str = CommandType.ACTION.value
    suite_id: str
    constantRefs: list[ConstantRefDto] = Field(default_factory=list)
    resultConstant: ResultConstantDto | None = None

    @model_validator(mode="after")
    def validate_configuration(self):
        self.suite_id = _normalize_token(self.suite_id)
        if not self.suite_id:
            raise ValueError("suite_id is required for runSuite.")
        normalized_constant_refs: list[ConstantRefDto] = []
        for item in self.constantRefs or []:
            normalized = _coerce_constant_ref(item)
            if normalized is not None:
                normalized_constant_refs.append(normalized)
        self.constantRefs = normalized_constant_refs
        self.resultConstant = _coerce_result_constant(self.resultConstant)
        return self


class AssertConfigurationCommandDto(ConfigurationCommandDto):
    commandCode: str
    commandType: str = CommandType.ASSERT.value
    error_message: str | None = None
    evaluated_object_type: str = AssertEvaluatedObjectType.JSON_DATA.value
    actualConstantRef: ConstantRefDto | None = None
    expected: object | None = None
    expected_json_array_id: str | None = None
    compare_keys: list[str] | None = None
    json_schema: dict | None = None

    @model_validator(mode="after")
    def validate_configuration(self):
        self.commandCode = _normalize_command_code(self.commandCode)
        supported_codes = {
            CommandCode.JSON_EQUALS.value,
            CommandCode.JSON_EMPTY.value,
            CommandCode.JSON_NOT_EMPTY.value,
            CommandCode.JSON_CONTAINS.value,
            CommandCode.JSON_ARRAY_EQUALS.value,
            CommandCode.JSON_ARRAY_EMPTY.value,
            CommandCode.JSON_ARRAY_NOT_EMPTY.value,
            CommandCode.JSON_ARRAY_CONTAINS.value,
        }
        if self.commandCode not in supported_codes:
            raise ValueError("Unsupported assert commandCode.")
        self.actualConstantRef = _coerce_constant_ref(self.actualConstantRef)
        self.evaluated_object_type = _normalize_path_token(self.evaluated_object_type).lower()
        self.expected_json_array_id = _normalize_token(self.expected_json_array_id) or None
        keys = _normalize_compare_keys(self.compare_keys)
        self.compare_keys = keys or None
        if self.actualConstantRef is None:
            raise ValueError("actualConstantRef is required for assert commands.")
        if self.commandCode in {
            CommandCode.JSON_ARRAY_EQUALS.value,
            CommandCode.JSON_ARRAY_CONTAINS.value,
        }:
            if not self.expected_json_array_id:
                raise ValueError("expected_json_array_id is required for jsonArray assert commands.")
            if not self.compare_keys:
                raise ValueError("compare_keys is required for jsonArray assert commands.")
        if self.commandCode == CommandCode.JSON_CONTAINS.value:
            if self.expected is None:
                raise ValueError("expected is required for jsonContains.")
            if not self.compare_keys:
                raise ValueError("compare_keys is required for jsonContains.")
        if self.commandCode == CommandCode.JSON_EQUALS.value and self.expected is None:
            raise ValueError("expected is required for jsonEquals.")
        return self

    @property
    def assert_type(self) -> str:
        mapping = {
            CommandCode.JSON_EQUALS.value: "equals",
            CommandCode.JSON_EMPTY.value: "empty",
            CommandCode.JSON_NOT_EMPTY.value: "not-empty",
            CommandCode.JSON_CONTAINS.value: "contains",
            CommandCode.JSON_ARRAY_EQUALS.value: "json-array-equals",
            CommandCode.JSON_ARRAY_EMPTY.value: "empty",
            CommandCode.JSON_ARRAY_NOT_EMPTY.value: "not-empty",
            CommandCode.JSON_ARRAY_CONTAINS.value: "json-array-contains",
        }
        return mapping[self.commandCode]


ConfigurationCommandTypes = (
    InitConstantConfigurationCommandDto
    | DeleteConstantConfigurationCommandDto
    | SleepConfigurationCommandDto
    | SendMessageQueueConfigurationCommandDto
    | SaveTableConfigurationCommandDto
    | DropTableConfigurationCommandDto
    | CleanTableConfigurationCommandDto
    | ExportDatasetConfigurationCommandDto
    | DropDatasetConfigurationCommandDto
    | CleanDatasetConfigurationCommandDto
    | RunSuiteConfigurationCommandDto
    | AssertConfigurationCommandDto
)


def convert_to_config_operation_type(data: dict):
    return convert_to_config_command_type(data)


def convert_to_config_command_type(data: dict):
    command_code = _normalize_command_code(
        _first_non_empty(data, "commandCode", "command_code", "operationType", "operation_type", "type")
    )
    if command_code == "assert":
        command_code = _derive_assert_command_code(data)
    command_type = _normalize_command_type(
        _first_non_empty(data, "commandType", "command_type")
    )

    if command_code == CommandCode.INIT_CONSTANT.value:
        return InitConstantConfigurationCommandDto(
            commandCode=command_code,
            commandType=command_type or CommandType.CONTEXT.value,
            definitionId=_first_non_empty(data, "definitionId", "definition_id"),
            name=_first_non_empty(data, "name", "key"),
            context=_first_non_empty(data, "context", "scope"),
            sourceType=_first_non_empty(data, "sourceType", "source_type"),
            value=_first_non_empty(data, "value", "data"),
            data=_first_non_empty(data, "data"),
            json_array_id=_first_non_empty(data, "json_array_id", "jsonArrayId"),
            dataset_id=_first_non_empty(data, "dataset_id", "datasetId", "data_source_id"),
            queue_id=_first_non_empty(data, "queue_id", "queueId"),
            retry=int(_first_non_empty(data, "retry") or 3),
            wait_time_seconds=int(_first_non_empty(data, "wait_time_seconds", "waitTimeSeconds") or 20),
            max_messages=int(_first_non_empty(data, "max_messages", "maxMessages") or 1000),
            target=_first_non_empty(data, "target"),
            key=_first_non_empty(data, "key"),
            scope=_first_non_empty(data, "scope"),
        )
    if command_code == CommandCode.DELETE_CONSTANT.value:
        return DeleteConstantConfigurationCommandDto(
            commandCode=command_code,
            commandType=command_type or CommandType.CONTEXT.value,
            targetConstantRef=_first_non_empty(data, "targetConstantRef", "target_constant_ref"),
        )
    if command_code == CommandCode.SLEEP.value:
        return SleepConfigurationCommandDto(
            commandCode=command_code,
            commandType=command_type or CommandType.ACTION.value,
            duration=int(_first_non_empty(data, "duration") or 0),
        )
    if command_code == CommandCode.SEND_MESSAGE_QUEUE.value:
        return SendMessageQueueConfigurationCommandDto(
            commandCode=command_code,
            commandType=command_type or CommandType.ACTION.value,
            queue_id=_first_non_empty(data, "queue_id", "queueId"),
            sourceConstantRef=_first_non_empty(data, "sourceConstantRef", "source_constant_ref"),
            template_id=_first_non_empty(data, "template_id", "templateId"),
            template_params=_first_non_empty(data, "template_params", "templateParams"),
            resultConstant=_first_non_empty(data, "resultConstant", "result_constant"),
        )
    if command_code == CommandCode.SAVE_TABLE.value:
        return SaveTableConfigurationCommandDto(
            commandCode=command_code,
            commandType=command_type or CommandType.ACTION.value,
            table_name=_first_non_empty(data, "table_name", "tableName"),
            sourceConstantRef=_first_non_empty(data, "sourceConstantRef", "source_constant_ref"),
            resultConstant=_first_non_empty(data, "resultConstant", "result_constant"),
        )
    if command_code == CommandCode.DROP_TABLE.value:
        return DropTableConfigurationCommandDto(
            commandCode=command_code,
            commandType=command_type or CommandType.ACTION.value,
            table_name=_first_non_empty(data, "table_name", "tableName"),
        )
    if command_code == CommandCode.CLEAN_TABLE.value:
        return CleanTableConfigurationCommandDto(
            commandCode=command_code,
            commandType=command_type or CommandType.ACTION.value,
            table_name=_first_non_empty(data, "table_name", "tableName"),
        )
    if command_code == CommandCode.EXPORT_DATASET.value:
        return ExportDatasetConfigurationCommandDto(
            commandCode=command_code,
            commandType=command_type or CommandType.ACTION.value,
            connection_id=_first_non_empty(data, "connection_id", "connectionId", "dataset_id", "datasetId"),
            table_name=_first_non_empty(data, "table_name", "tableName"),
            sourceConstantRef=_first_non_empty(data, "sourceConstantRef", "source_constant_ref"),
            mode=_first_non_empty(data, "mode", "export_mode", "exportMode") or "append",
            mapping_keys=_normalize_compare_keys(_first_non_empty(data, "mapping_keys", "mappingKeys")),
            dataset_description=_first_non_empty(data, "dataset_description", "datasetDescription"),
            dataset_id=_first_non_empty(data, "dataset_id", "datasetId"),
            resultConstant=_first_non_empty(data, "resultConstant", "result_constant"),
        )
    if command_code == CommandCode.DROP_DATASET.value:
        return DropDatasetConfigurationCommandDto(
            commandCode=command_code,
            commandType=command_type or CommandType.ACTION.value,
            dataset_id=_first_non_empty(data, "dataset_id", "datasetId"),
        )
    if command_code == CommandCode.CLEAN_DATASET.value:
        return CleanDatasetConfigurationCommandDto(
            commandCode=command_code,
            commandType=command_type or CommandType.ACTION.value,
            dataset_id=_first_non_empty(data, "dataset_id", "datasetId"),
        )
    if command_code == CommandCode.RUN_SUITE.value:
        return RunSuiteConfigurationCommandDto(
            commandCode=command_code,
            commandType=command_type or CommandType.ACTION.value,
            suite_id=_first_non_empty(data, "suite_id", "suiteId"),
            constantRefs=_first_non_empty(data, "constantRefs", "constant_refs") or [],
            resultConstant=_first_non_empty(data, "resultConstant", "result_constant"),
        )
    if command_code in {
        CommandCode.JSON_EQUALS.value,
        CommandCode.JSON_EMPTY.value,
        CommandCode.JSON_NOT_EMPTY.value,
        CommandCode.JSON_CONTAINS.value,
        CommandCode.JSON_ARRAY_EQUALS.value,
        CommandCode.JSON_ARRAY_EMPTY.value,
        CommandCode.JSON_ARRAY_NOT_EMPTY.value,
        CommandCode.JSON_ARRAY_CONTAINS.value,
    }:
        return AssertConfigurationCommandDto(
            commandCode=command_code,
            commandType=command_type or CommandType.ASSERT.value,
            error_message=_first_non_empty(data, "error_message", "errorMessage"),
            evaluated_object_type=_first_non_empty(
                data,
                "evaluated_object_type",
                "evaluetedObjectType",
                "evaluatedObjectType",
            ) or AssertEvaluatedObjectType.JSON_DATA.value,
            actualConstantRef=_first_non_empty(data, "actualConstantRef", "actual_constant_ref"),
            expected=_first_non_empty(data, "expected"),
            expected_json_array_id=_first_non_empty(
                data,
                "expected_json_array_id",
                "expectedJsonArrayId",
                "json_array_id",
            ),
            compare_keys=_normalize_compare_keys(_first_non_empty(data, "compare_keys", "compareKeys")),
            json_schema=_first_non_empty(data, "json_schema", "jsonSchema"),
        )
    raise ValueError(f"Unsupported command code: {command_code}")


# Backward import aliases used by the current codebase during the refactor.
ConfigurationOperationDto = ConfigurationCommandDto
ConfigurationOperationTypes = ConfigurationCommandTypes
DataConfigurationOperationDto = InitConstantConfigurationCommandDto
DataFromJsonArrayConfigurationOperationDto = InitConstantConfigurationCommandDto
DataFromDbConfigurationOperationDto = InitConstantConfigurationCommandDto
DataFromQueueConfigurationOperationDto = InitConstantConfigurationCommandDto
SleepConfigurationOperationDto = SleepConfigurationCommandDto
PublishConfigurationOperationDto = SendMessageQueueConfigurationCommandDto
SaveInternalDBConfigurationOperationDto = SaveTableConfigurationCommandDto
SaveToExternalDBConfigurationOperationDto = ExportDatasetConfigurationCommandDto
RunSuiteConfigurationOperationDto = RunSuiteConfigurationCommandDto
SetVarConfigurationOperationDto = InitConstantConfigurationCommandDto
AssertConfigurationOperationDto = AssertConfigurationCommandDto
SetResponseStatusConfigurationOperationDto = ConfigurationCommandDto
SetResponseHeaderConfigurationOperationDto = ConfigurationCommandDto
SetResponseBodyConfigurationOperationDto = ConfigurationCommandDto
BuildResponseFromTemplateConfigurationOperationDto = ConfigurationCommandDto
