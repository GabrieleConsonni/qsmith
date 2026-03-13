import pytest

from app.elaborations.models.dtos.configuration_operation_dto import (
    DataConfigurationOperationDto,
    PublishConfigurationOperationDto,
    SetResponseStatusConfigurationOperationDto,
)
from app.elaborations.services.operations.operation_policy_validator import (
    validate_operation_policy,
)
from app.elaborations.services.operations.operation_scope import (
    SCOPE_MOCK_PRE_RESPONSE,
    SCOPE_MOCK_RESPONSE,
    SCOPE_TEST,
)


def test_policy_blocks_global_target_in_test_scope():
    cfg = DataConfigurationOperationDto(data=[{"id": 1}], target="$.global.rows")

    with pytest.raises(
        ValueError,
        match="Global context is immutable during test execution.",
    ):
        validate_operation_policy(cfg, SCOPE_TEST)


def test_policy_blocks_side_effect_operation_in_mock_pre_response():
    cfg = PublishConfigurationOperationDto(queue_id="queue-1")

    with pytest.raises(
        ValueError,
        match="not allowed in scope 'mock.preResponse'",
    ):
        validate_operation_policy(cfg, SCOPE_MOCK_PRE_RESPONSE)


def test_policy_allows_mock_response_operation_in_response_scope():
    cfg = SetResponseStatusConfigurationOperationDto(status=201)

    contract = validate_operation_policy(cfg, SCOPE_MOCK_RESPONSE)

    assert contract.family == "mock-response"
