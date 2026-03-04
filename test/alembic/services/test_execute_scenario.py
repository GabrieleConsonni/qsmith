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
from app.elaborations.services.alembic.scenario_execution_service import ScenarioExecutionService
from app.elaborations.services.alembic.scenario_service import ScenarioService
from app.elaborations.services.alembic.scenario_step_execution_service import (
    ScenarioStepExecutionService,
)
from app.elaborations.services.alembic.scenario_step_service import ScenarioStepService
from app.elaborations.services.alembic.step_operation_execution_service import (
    StepOperationExecutionService,
)
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
                step_type=StepType.DATA.value,
                configuration_json={
                    "stepType": "data",
                    "data": [{"id": 1}],
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
                code="step1_code",
                step_type=StepType.DATA.value,
                configuration_json={
                    "stepType": "data",
                    "data": [{"id": 1}],
                },
                order=0,
            )
        )
        StepOperationService().insert(
            session,
            StepOperationEntity(
                scenario_step_id=scenario_step_id,
                code="operation_1",
                operation_type=OperationType.SAVE_INTERNAL_DB.value,
                configuration_json={
                    "operationType": "save-internal-db",
                    "table_name": "test_table",
                },
                order=0,
            )
        )

    _execute(ScenarioExecutionInput(
        execution_id=str(uuid4()),
        scenario_id=scenario_id,
        scenario_code="scenario_code"
    ))

    with managed_session() as session:
        scenario_executions = ScenarioExecutionService().get_all_by_scenario_id(
            session,
            scenario_id=scenario_id,
            limit=10,
        )
        assert len(scenario_executions) == 1
        scenario_execution = scenario_executions[0]
        assert str(scenario_execution.status or "").strip().lower() == "success"
        assert scenario_execution.finished_at is not None

        step_executions = ScenarioStepExecutionService().get_all_by_execution_id(
            session,
            scenario_execution.id,
        )
        assert len(step_executions) == 1
        step_execution = step_executions[0]
        assert str(step_execution.status or "").strip().lower() == "success"
        assert step_execution.finished_at is not None

        operation_executions = StepOperationExecutionService().get_all_by_step_execution_id(
            session,
            step_execution.id,
        )
        assert len(operation_executions) == 1
        operation_execution = operation_executions[0]
        assert str(operation_execution.status or "").strip().lower() == "success"
        assert operation_execution.finished_at is not None

        logs = LogService().get_logs(session)
        assert len(logs) > 0


def test_execution_with_assert_failure_marks_error_statuses(alembic_container):
    with managed_session() as session:
        scenario_id = ScenarioService().insert(
            session,
            ScenarioEntity(code="scenario_assert_error"),
        )
        scenario_step_id = ScenarioStepService().insert(
            session,
            ScenarioStepEntity(
                scenario_id=scenario_id,
                code="step_assert_error",
                step_type=StepType.DATA.value,
                configuration_json={
                    "stepType": "data",
                    "data": [{"id": 1, "code": "A"}],
                },
                order=0,
            ),
        )
        StepOperationService().insert(
            session,
            StepOperationEntity(
                scenario_step_id=scenario_step_id,
                code="assert_empty",
                operation_type=OperationType.ASSERT.value,
                configuration_json={
                    "operationType": "assert",
                    "evaluated_object_type": "json-data",
                    "assert_type": "empty",
                    "error_message": "Expected no rows from step.",
                },
                order=0,
            ),
        )

    _execute(
        ScenarioExecutionInput(
            execution_id=str(uuid4()),
            scenario_id=scenario_id,
            scenario_code="scenario_assert_error",
        )
    )

    with managed_session() as session:
        scenario_executions = ScenarioExecutionService().get_all_by_scenario_id(
            session,
            scenario_id=scenario_id,
            limit=10,
        )
        assert len(scenario_executions) == 1
        scenario_execution = scenario_executions[0]
        assert str(scenario_execution.status or "").strip().lower() == "error"
        assert scenario_execution.finished_at is not None
        assert "Expected no rows from step." in str(scenario_execution.error_message or "")

        step_executions = ScenarioStepExecutionService().get_all_by_execution_id(
            session,
            scenario_execution.id,
        )
        assert len(step_executions) == 1
        step_execution = step_executions[0]
        assert str(step_execution.status or "").strip().lower() == "error"
        assert step_execution.finished_at is not None
        assert "Expected no rows from step." in str(step_execution.error_message or "")

        operation_executions = StepOperationExecutionService().get_all_by_step_execution_id(
            session,
            step_execution.id,
        )
        assert len(operation_executions) == 1
        operation_execution = operation_executions[0]
        assert str(operation_execution.status or "").strip().lower() == "error"
        assert operation_execution.finished_at is not None
        assert "Expected no rows from step." in str(operation_execution.error_message or "")


if __name__ == "__main__":
    unittest.main()
