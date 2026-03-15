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
from _alembic.models.suite_entity import SuiteEntity
from _alembic.models.suite_execution_entity import SuiteExecutionEntity
from _alembic.models.suite_test_entity import SuiteTestEntity
from _alembic.models.suite_test_execution_entity import SuiteTestExecutionEntity
from _alembic.models.test_entity import TestEntity
from _alembic.models.test_operation_execution_entity import TestOperationExecutionEntity
from _alembic.models.test_operation_entity import TestOperationEntity
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
    | SuiteEntity
    | SuiteExecutionEntity
    | SuiteTestEntity
    | SuiteTestExecutionEntity
    | TestEntity
    | TestOperationEntity
    | TestOperationExecutionEntity
    | SuiteItemEntity
    | SuiteItemExecutionEntity
    | SuiteItemOperationEntity
    | SuiteItemOperationExecutionEntity
    | TestSuiteEntity
    | TestSuiteExecutionEntity
)
