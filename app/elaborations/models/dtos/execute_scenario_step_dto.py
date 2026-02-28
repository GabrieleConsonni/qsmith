from pydantic import BaseModel


class ExecuteScenarioStepDto(BaseModel):
    include_previous: bool = False

