from pydantic import BaseModel, Field

from elaborations.models.dtos.configuration_operation_dto import ConfigurationOperationTypes
from elaborations.models.dtos.configuration_step_dtos import ConfigurationStepDtoTypes
from elaborations.models.enums.on_failure import OnFailure


class CreateStepOperationDto(BaseModel):
    order: int
    code: str | None = None
    description: str | None = ""
    cfg: ConfigurationOperationTypes | None = None
    operation_id: str | None = None

class CreateScenarioStepDto(BaseModel):
    order: int
    code: str | None = None
    description: str | None = ""
    step_type: str | None = None
    cfg: ConfigurationStepDtoTypes | None = None
    step_id: str | None = None
    on_failure: str | None = OnFailure.ABORT
    operations: list[CreateStepOperationDto] = Field(default_factory=list)


class CreateScenarioDto(BaseModel):
    code: str
    description: str
    steps: list[CreateScenarioStepDto] = Field(default_factory=list)


class UpdateScenarioDto(CreateScenarioDto):
    id: str


