from pydantic import BaseModel, Field

from elaborations.models.enums.on_failure import OnFailure


class CreateStepOperationDto(BaseModel):
    order: int
    operation_id: str

class CreateScenarioStepDto(BaseModel):
    order: int
    step_id: str
    description: str | None = ""
    on_failure: str | None = OnFailure.ABORT
    operations: list[CreateStepOperationDto] = Field(default_factory=list)


class CreateScenarioDto(BaseModel):
    code: str
    description: str
    steps: list[CreateScenarioStepDto] = Field(default_factory=list)


class UpdateScenarioDto(CreateScenarioDto):
    id: str


