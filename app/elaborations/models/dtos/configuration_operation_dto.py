from pydantic import BaseModel

from elaborations.models.enums.operation_type import OperationType


class ConfigurationOperationDto(BaseModel):
    operationType: str

class PublishConfigurationOperationDto(ConfigurationOperationDto):
    operationType: str = OperationType.PUBLISH.value
    queue_id:str
    template_id: str | None = None
    template_params: dict | None = None

class SaveInternalDBConfigurationOperationDto(ConfigurationOperationDto):
    operationType: str = OperationType.SAVE_INTERNAL_DB.value
    table_name: str

class SaveToExternalDBConfigurationOperationDto(ConfigurationOperationDto):
    operationType: str = OperationType.SAVE_EXTERNAL_DB.value
    connection_id: str | None = None
    table_name: str | None = None

ConfigurationOperationTypes = PublishConfigurationOperationDto | SaveInternalDBConfigurationOperationDto | SaveToExternalDBConfigurationOperationDto

def convert_to_config_operation_type(data: dict):
    operation_type = data.get("operationType")
    if operation_type == OperationType.PUBLISH.value:
        return PublishConfigurationOperationDto(
            queue_id=data.get("queue_id")
        )
    elif operation_type == OperationType.SAVE_INTERNAL_DB.value:
        return SaveInternalDBConfigurationOperationDto(
            table_name=data.get("table_name")
        )
    elif operation_type == OperationType.SAVE_EXTERNAL_DB.value:
        return SaveToExternalDBConfigurationOperationDto(
            connection_id=data.get("connection_id"),
            table_name=data.get("table_name")
        )
    else:
        raise ValueError(f"Unsupported operation type: {operation_type}")
