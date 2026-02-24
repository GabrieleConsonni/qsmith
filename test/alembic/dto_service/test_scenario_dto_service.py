import asyncio
import unittest

from app._alembic.models.operation_entity import OperationEntity
from app._alembic.models.step_entity import StepEntity
from app._alembic.services.session_context_manager import managed_session
from app.elaborations.api.scenarios_api import insert_scenario_api
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


def test_insert_scenario(alembic_container):

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

    scenario_dto: CreateScenarioDto = CreateScenarioDto(
        code="Test Scenario",
        description="This is a test scenario",
        steps=[
            CreateScenarioStepDto(
                step_id=step_id,
                order=0,
                cfg=SleepConfigurationStepDto(duration=5),
                operations=[
                    CreateStepOperationDto(
                        operation_id=operation_id,
                        order=0,
                        cfg=SaveInternalDBConfigurationOperationDto(
                            table_name="test_table"
                        )
                    )
                ]
            )
        ]
    )

    scenario_id = asyncio.run(insert_scenario_api(scenario_dto))["id"]

    with managed_session() as session:

        scenario_entity = ScenarioService().get_by_id(session, scenario_id)

        assert scenario_entity is not None
        assert scenario_entity.code == "Test Scenario"
        assert scenario_entity.description == "This is a test scenario"

        steps = ScenarioStepService().get_all_by_scenario_id(session, scenario_id)
        assert len(steps) == 1
        assert steps[0].order == 0
        assert steps[0].step_id == step_id

        operations = StepOperationService().get_all_by_step(session, steps[0].id)
        assert len(operations) == 1
        assert operations[0].order == 0
        assert operations[0].operation_id == operation_id


if __name__ == "__main__":
    unittest.main()
