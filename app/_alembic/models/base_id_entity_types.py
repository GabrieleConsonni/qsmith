from _alembic.models.json_payload_entity import JsonPayloadEntity
from _alembic.models.log_entity import LogEntity
from _alembic.models.mock_server_api_entity import MockServerApiEntity
from _alembic.models.mock_server_entity import MockServerEntity
from _alembic.models.mock_server_invocation_entity import MockServerInvocationEntity
from _alembic.models.mock_server_queue_entity import MockServerQueueEntity
from _alembic.models.ms_api_operation_entity import MsApiOperationEntity
from _alembic.models.ms_queue_operation_entity import MsQueueOperationEntity
from _alembic.models.operation_entity import OperationEntity
from _alembic.models.queue_entity import QueueEntity
from _alembic.models.scenario_entity import ScenarioEntity
from _alembic.models.scenario_execution_entity import ScenarioExecutionEntity
from _alembic.models.scenario_step_entity import ScenarioStepEntity
from _alembic.models.scenario_step_execution_entity import ScenarioStepExecutionEntity
from _alembic.models.step_entity import StepEntity
from _alembic.models.step_operation_execution_entity import StepOperationExecutionEntity
from _alembic.models.step_operation_entity import StepOperationEntity
from _alembic.models.suite_item_entity import SuiteItemEntity
from _alembic.models.suite_item_execution_entity import SuiteItemExecutionEntity
from _alembic.models.suite_item_operation_entity import SuiteItemOperationEntity
from _alembic.models.suite_item_operation_execution_entity import (
    SuiteItemOperationExecutionEntity,
)
from _alembic.models.test_suite_entity import TestSuiteEntity
from _alembic.models.test_suite_execution_entity import TestSuiteExecutionEntity

BaseIdEntityTypes = (
    JsonPayloadEntity
    | LogEntity
    | MockServerEntity
    | MockServerApiEntity
    | MockServerInvocationEntity
    | MockServerQueueEntity
    | MsApiOperationEntity
    | MsQueueOperationEntity
    | OperationEntity
    | QueueEntity
    | ScenarioEntity
    | ScenarioExecutionEntity
    | ScenarioStepEntity
    | ScenarioStepExecutionEntity
    | StepEntity
    | StepOperationEntity
    | StepOperationExecutionEntity
    | SuiteItemEntity
    | SuiteItemExecutionEntity
    | SuiteItemOperationEntity
    | SuiteItemOperationExecutionEntity
    | TestSuiteEntity
    | TestSuiteExecutionEntity
)
