import json
import unittest

from app._alembic.models.operation_entity import OperationEntity
from app._alembic.models.scenario_entity import ScenarioEntity
from app._alembic.models.scenario_step_entity import ScenarioStepEntity
from app._alembic.models.step_entity import StepEntity
from app._alembic.models.step_operation_entity import StepOperationEntity
from app._alembic.services.session_context_manager import managed_session
from app.elaborations.models.enums.operation_type import OperationType
from app.elaborations.models.enums.step_type import StepType
from app.elaborations.services.alembic.operation_service import OperationService
from app.elaborations.services.alembic.scenario_service import ScenarioService
from app.elaborations.services.alembic.scenario_step_service import ScenarioStepService
from app.elaborations.services.alembic.step_operation_service import StepOperationService
from app.elaborations.services.alembic.step_service import StepService
from app.elaborations.services.scenarios.scenario_executor_thread import ScenarioExecutionInput, _execute
from app.logs.services.alembic.log_service import LogService
from uuid import uuid4


def test_execution(alembic_container):
    with managed_session() as session:
        step_id = StepService().insert(
            session,
            StepEntity(
                code="step1_code",
                step_type=StepType.SLEEP.value,
                configuration_json={
                    "stepType": "sleep",
                    "duration": 2
                }
            )
        )
        operation_id = OperationService().insert(
            session,
            OperationEntity(
                code="operation_1",
                operation_type=OperationType.SAVE_INTERNAL_DB.value,
                configuration_json={
                    "operationType": "save-internal-db",
                    "table_name": "test_table"
                }
            )
        )
        scenario_id = ScenarioService().insert(
            session,
            ScenarioEntity(
                code="scenario_code"
            )
        )
        scenario_step_id = ScenarioStepService().insert(
            session,
            ScenarioStepEntity(
                scenario_id=scenario_id,
                step_id=step_id,
                order=0
            )
        )
        StepOperationService().insert(
            session,
            StepOperationEntity(
                scenario_step_id=scenario_step_id,
                operation_id=operation_id,
                order=0
            )
        )

    _execute(ScenarioExecutionInput(
        execution_id=str(uuid4()),
        scenario_id=scenario_id,
        scenario_code="scenario_code"
    ))

    with managed_session() as session:
        logs = LogService().get_logs(session)

        for log in logs:
            print(f" {log.level} - {log.message} - {json.dumps(log.payload)} ")


if __name__ == "__main__":
    unittest.main()
