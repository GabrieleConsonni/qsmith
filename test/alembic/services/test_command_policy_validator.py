import pytest

from app.elaborations.models.dtos.configuration_command_dto import (
    AssertConfigurationCommandDto,
    DataConfigurationOperationDto,
    PublishConfigurationOperationDto,
)
from app.elaborations.services.operations.command_policy_validator import (
    validate_operation_policy,
)
from app.elaborations.services.operations.command_scope import (
    SCOPE_MOCK_PRE_RESPONSE,
    SCOPE_TEST,
)


def test_policy_blocks_global_target_in_test_scope():
    cfg = DataConfigurationOperationDto(
        name="rows",
        context="global",
        sourceType="json",
        data=[{"id": 1}],
        target="$.global.rows",
    )

    with pytest.raises(
        ValueError,
        match="Global context is immutable during test execution.",
    ):
        validate_operation_policy(cfg, SCOPE_TEST)


def test_policy_blocks_side_effect_command_in_mock_pre_response():
    cfg = PublishConfigurationOperationDto(queue_id="queue-1")

    with pytest.raises(
        ValueError,
        match="not allowed in scope 'mock.preResponse'",
    ):
        validate_operation_policy(cfg, SCOPE_MOCK_PRE_RESPONSE)


def test_policy_allows_assert_in_mock_pre_response():
    cfg = AssertConfigurationCommandDto(
        commandCode="jsonEmpty",
        commandType="assert",
        actual={"$ref": "$.runEnvelope.event.payload"},
    )

    contract = validate_operation_policy(cfg, SCOPE_MOCK_PRE_RESPONSE)

    assert contract.family == "assert"

