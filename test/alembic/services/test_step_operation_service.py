import unittest

from app._alembic.models.operation_entity import OperationEntity
from app._alembic.models.scenario_entity import ScenarioEntity
from app._alembic.models.scenario_step_entity import ScenarioStepEntity
from app._alembic.models.step_entity import StepEntity
from app._alembic.models.step_operation_entity import StepOperationEntity
from app._alembic.services.session_context_manager import managed_session
from app.elaborations.models.dtos.configuration_operation_dto import SaveInternalDBConfigurationOperationDto
from app.elaborations.models.dtos.configuration_step_dtos import SleepConfigurationStepDto
from app.elaborations.models.dtos.create_scenario_dto import CreateScenarioDto, CreateScenarioStepDto, \
    CreateStepOperationDto
from app.elaborations.models.enums.operation_type import OperationType
from app.elaborations.models.enums.step_type import StepType
from app.elaborations.services.alembic.operation_service import OperationService
from app.elaborations.services.alembic.scenario_service import ScenarioService
from app.elaborations.services.alembic.step_service import StepService
from app.elaborations.services.alembic.scenario_step_service import ScenarioStepService
from app.elaborations.services.alembic.step_operation_service import StepOperationService


def test_delete(alembic_container):
    with managed_session() as session:
        step_id = StepService().insert(
            session,
            StepEntity(
                code="step1_code",
                step_type=StepType.SLEEP.value,
                configuration_json={"param": "value"}
            )
        )
        operation_id = OperationService().insert(
            session,
            OperationEntity(
                code="operation_1",
                operation_type=OperationType.SAVE_INTERNAL_DB.value,
                configuration_json={"table_name": "test_table"}
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
                step_type=StepType.SLEEP.value,
                configuration_json={"stepType": "sleep", "duration": 1},
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

    with managed_session() as session:
        deleted = ScenarioService().delete_by_id(session, scenario_id)
        assert deleted == 1

        step = ScenarioStepService().get_by_id(session, scenario_step_id)
        assert step is None

        operations = StepOperationService().get_all_by_step(session, scenario_step_id)
        assert 0 == len(operations)

if __name__ == "__main__":
    unittest.main()
