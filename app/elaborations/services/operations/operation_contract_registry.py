from dataclasses import dataclass

from elaborations.models.enums.operation_type import OperationType
from elaborations.services.operations.operation_scope import (
    SCOPE_HOOK_AFTER_ALL,
    SCOPE_HOOK_AFTER_EACH,
    SCOPE_HOOK_BEFORE_ALL,
    SCOPE_HOOK_BEFORE_EACH,
    SCOPE_MOCK_POST_RESPONSE,
    SCOPE_MOCK_PRE_RESPONSE,
    SCOPE_MOCK_RESPONSE,
    SCOPE_TEST,
)


@dataclass(frozen=True)
class OperationContract:
    family: str
    name: str
    supported_scopes: tuple[str, ...]
    reads_from: tuple[str, ...]
    writes_to: tuple[str, ...]
    produces_result: bool
    side_effects: bool
    async_allowed: bool
    failure_mode: str


_HOOK_AND_TEST_SCOPES = (
    SCOPE_TEST,
    SCOPE_HOOK_BEFORE_ALL,
    SCOPE_HOOK_BEFORE_EACH,
    SCOPE_HOOK_AFTER_EACH,
    SCOPE_HOOK_AFTER_ALL,
)
_ALL_SCOPES = (
    SCOPE_TEST,
    SCOPE_HOOK_BEFORE_ALL,
    SCOPE_HOOK_BEFORE_EACH,
    SCOPE_HOOK_AFTER_EACH,
    SCOPE_HOOK_AFTER_ALL,
    SCOPE_MOCK_PRE_RESPONSE,
    SCOPE_MOCK_RESPONSE,
    SCOPE_MOCK_POST_RESPONSE,
)

_CONTRACTS: dict[str, OperationContract] = {
    OperationType.DATA.value: OperationContract(
        family="input",
        name=OperationType.DATA.value,
        supported_scopes=_HOOK_AND_TEST_SCOPES,
        reads_from=("event", "global", "local"),
        writes_to=("local",),
        produces_result=True,
        side_effects=False,
        async_allowed=False,
        failure_mode="fail-fast",
    ),
    OperationType.DATA_FROM_JSON_ARRAY.value: OperationContract(
        family="input",
        name=OperationType.DATA_FROM_JSON_ARRAY.value,
        supported_scopes=_HOOK_AND_TEST_SCOPES,
        reads_from=("global", "local"),
        writes_to=("local",),
        produces_result=True,
        side_effects=False,
        async_allowed=False,
        failure_mode="fail-fast",
    ),
    OperationType.DATA_FROM_DB.value: OperationContract(
        family="input",
        name=OperationType.DATA_FROM_DB.value,
        supported_scopes=_HOOK_AND_TEST_SCOPES,
        reads_from=("global", "local"),
        writes_to=("local",),
        produces_result=True,
        side_effects=False,
        async_allowed=False,
        failure_mode="fail-fast",
    ),
    OperationType.DATA_FROM_QUEUE.value: OperationContract(
        family="input",
        name=OperationType.DATA_FROM_QUEUE.value,
        supported_scopes=_HOOK_AND_TEST_SCOPES,
        reads_from=("global", "local"),
        writes_to=("local",),
        produces_result=True,
        side_effects=False,
        async_allowed=False,
        failure_mode="fail-fast",
    ),
    OperationType.SLEEP.value: OperationContract(
        family="utility",
        name=OperationType.SLEEP.value,
        supported_scopes=_HOOK_AND_TEST_SCOPES,
        reads_from=("local",),
        writes_to=(),
        produces_result=True,
        side_effects=False,
        async_allowed=False,
        failure_mode="fail-fast",
    ),
    OperationType.PUBLISH.value: OperationContract(
        family="action",
        name=OperationType.PUBLISH.value,
        supported_scopes=(
            *_HOOK_AND_TEST_SCOPES,
            SCOPE_MOCK_POST_RESPONSE,
        ),
        reads_from=("global", "local", "event"),
        writes_to=("local",),
        produces_result=True,
        side_effects=True,
        async_allowed=True,
        failure_mode="fail-fast",
    ),
    OperationType.SAVE_INTERNAL_DB.value: OperationContract(
        family="action",
        name=OperationType.SAVE_INTERNAL_DB.value,
        supported_scopes=(
            *_HOOK_AND_TEST_SCOPES,
            SCOPE_MOCK_POST_RESPONSE,
        ),
        reads_from=("global", "local", "event"),
        writes_to=("local",),
        produces_result=True,
        side_effects=True,
        async_allowed=True,
        failure_mode="fail-fast",
    ),
    OperationType.SAVE_EXTERNAL_DB.value: OperationContract(
        family="action",
        name=OperationType.SAVE_EXTERNAL_DB.value,
        supported_scopes=(
            *_HOOK_AND_TEST_SCOPES,
            SCOPE_MOCK_POST_RESPONSE,
        ),
        reads_from=("global", "local", "event"),
        writes_to=("local",),
        produces_result=True,
        side_effects=True,
        async_allowed=True,
        failure_mode="fail-fast",
    ),
    OperationType.RUN_SUITE.value: OperationContract(
        family="trigger",
        name=OperationType.RUN_SUITE.value,
        supported_scopes=(
            *_HOOK_AND_TEST_SCOPES,
            SCOPE_MOCK_POST_RESPONSE,
        ),
        reads_from=("global", "local", "event"),
        writes_to=("local",),
        produces_result=True,
        side_effects=True,
        async_allowed=True,
        failure_mode="fail-fast",
    ),
    "run-suite": OperationContract(
        family="trigger",
        name="run-suite",
        supported_scopes=(
            *_HOOK_AND_TEST_SCOPES,
            SCOPE_MOCK_POST_RESPONSE,
        ),
        reads_from=("global", "local", "event"),
        writes_to=("local",),
        produces_result=True,
        side_effects=True,
        async_allowed=True,
        failure_mode="fail-fast",
    ),
    OperationType.SET_VAR.value: OperationContract(
        family="context",
        name=OperationType.SET_VAR.value,
        supported_scopes=_ALL_SCOPES,
        reads_from=("global", "local", "event", "artifacts"),
        writes_to=("global", "local"),
        produces_result=True,
        side_effects=False,
        async_allowed=False,
        failure_mode="fail-fast",
    ),
    OperationType.ASSERT.value: OperationContract(
        family="assert",
        name=OperationType.ASSERT.value,
        supported_scopes=(
            *_HOOK_AND_TEST_SCOPES,
            SCOPE_MOCK_PRE_RESPONSE,
            SCOPE_MOCK_POST_RESPONSE,
        ),
        reads_from=("global", "local", "event", "artifacts"),
        writes_to=("artifacts",),
        produces_result=True,
        side_effects=False,
        async_allowed=False,
        failure_mode="fail-fast",
    ),
    "set-response-status": OperationContract(
        family="mock-response",
        name="set-response-status",
        supported_scopes=(SCOPE_MOCK_RESPONSE,),
        reads_from=("global", "local", "event", "response"),
        writes_to=("response",),
        produces_result=True,
        side_effects=False,
        async_allowed=False,
        failure_mode="fail-fast",
    ),
    "set-response-header": OperationContract(
        family="mock-response",
        name="set-response-header",
        supported_scopes=(SCOPE_MOCK_RESPONSE,),
        reads_from=("global", "local", "event", "response"),
        writes_to=("response",),
        produces_result=True,
        side_effects=False,
        async_allowed=False,
        failure_mode="fail-fast",
    ),
    "set-response-body": OperationContract(
        family="mock-response",
        name="set-response-body",
        supported_scopes=(SCOPE_MOCK_RESPONSE,),
        reads_from=("global", "local", "event", "response"),
        writes_to=("response",),
        produces_result=True,
        side_effects=False,
        async_allowed=False,
        failure_mode="fail-fast",
    ),
    "build-response-from-template": OperationContract(
        family="mock-response",
        name="build-response-from-template",
        supported_scopes=(SCOPE_MOCK_RESPONSE,),
        reads_from=("global", "local", "event", "response"),
        writes_to=("response",),
        produces_result=True,
        side_effects=False,
        async_allowed=False,
        failure_mode="fail-fast",
    ),
}


def get_operation_contract(operation_type: str) -> OperationContract | None:
    normalized = str(operation_type or "").strip().replace("_", "-").lower()
    return _CONTRACTS.get(normalized)
