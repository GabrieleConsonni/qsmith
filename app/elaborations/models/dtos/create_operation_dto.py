from pydantic import BaseModel

from elaborations.models.dtos.configuration_operation_dto import ConfigurationOperationTypes


class CreateOperationDto(BaseModel):
    description: str
    cfg: ConfigurationOperationTypes
