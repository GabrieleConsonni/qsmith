from _alembic.models.json_payload_entity import JsonPayloadEntity
from _alembic.models.log_entity import LogEntity
from _alembic.models.operation_entity import OperationEntity
from _alembic.models.queue_entity import QueueEntity
from _alembic.models.scenario_entity import ScenarioEntity
from _alembic.models.scenario_execution_entity import ScenarioExecutionEntity
from _alembic.models.scenario_step_entity import ScenarioStepEntity
from _alembic.models.scenario_step_execution_entity import ScenarioStepExecutionEntity
from _alembic.models.step_entity import StepEntity
from _alembic.models.step_operation_execution_entity import StepOperationExecutionEntity
from _alembic.models.step_operation_entity import StepOperationEntity

BaseIdEntityTypes = (
    JsonPayloadEntity
    | LogEntity
    | OperationEntity
    | QueueEntity
    | ScenarioEntity
    | ScenarioExecutionEntity
    | ScenarioStepEntity
    | ScenarioStepExecutionEntity
    | StepEntity
    | StepOperationEntity
    | StepOperationExecutionEntity
)
