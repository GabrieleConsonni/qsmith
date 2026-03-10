from pydantic import BaseModel, Field, model_validator

from elaborations.models.dtos.configuration_operation_dto import ConfigurationOperationTypes
from elaborations.models.enums.hook_phase import HookPhase
from elaborations.models.enums.on_failure import OnFailure
from elaborations.models.enums.suite_item_kind import SuiteItemKind


class CreateSuiteItemOperationDto(BaseModel):
    order: int
    code: str | None = None
    description: str | None = ""
    cfg: ConfigurationOperationTypes | None = None
    operation_id: str | None = None


class CreateSuiteItemDto(BaseModel):
    kind: str = SuiteItemKind.TEST.value
    hook_phase: str | None = None
    code: str | None = None
    description: str | None = ""
    on_failure: str | None = OnFailure.ABORT.value
    operations: list[CreateSuiteItemOperationDto] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_item(self):
        normalized_kind = str(self.kind or SuiteItemKind.TEST.value).strip().lower()
        if normalized_kind not in {item.value for item in SuiteItemKind}:
            raise ValueError(f"Unsupported suite item kind: {self.kind}")
        self.kind = normalized_kind

        normalized_code = str(self.code or "").strip()
        normalized_hook_phase = str(self.hook_phase or "").strip().lower() or None
        self.description = str(self.description or "")
        self.on_failure = str(self.on_failure or OnFailure.ABORT.value).strip().upper()
        if self.on_failure not in {OnFailure.ABORT.value, OnFailure.CONTINUE.value}:
            self.on_failure = OnFailure.ABORT.value

        if self.kind == SuiteItemKind.HOOK.value:
            if normalized_hook_phase not in {phase.value for phase in HookPhase}:
                raise ValueError("hook_phase is required for hook suite items.")
            self.hook_phase = normalized_hook_phase
            self.code = normalized_code or normalized_hook_phase
        else:
            if not normalized_code:
                raise ValueError("code is required for test suite items.")
            self.code = normalized_code
            self.hook_phase = None

        return self


class CreateTestSuiteDto(BaseModel):
    code: str
    description: str
    tests: list[CreateSuiteItemDto] = Field(default_factory=list)
    hooks: list[CreateSuiteItemDto] = Field(default_factory=list)


class UpdateTestSuiteDto(CreateTestSuiteDto):
    id: str
