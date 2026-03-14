from pydantic import BaseModel


class ExecuteSuiteTestDto(BaseModel):
    include_previous: bool = False

