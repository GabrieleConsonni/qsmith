from fastapi import APIRouter

from _alembic.models.scenario_entity import ScenarioEntity
from _alembic.models.scenario_step_entity import ScenarioStepEntity
from _alembic.models.step_operation_entity import StepOperationEntity
from _alembic.services.session_context_manager import managed_session
from elaborations.models.dtos.create_scenario_dto import (
    CreateScenarioDto,
    CreateScenarioStepDto,
    CreateStepOperationDto,
    UpdateScenarioDto,
)
from elaborations.models.dtos.execute_scenario_step_dto import ExecuteScenarioStepDto
from elaborations.services.alembic.scenario_service import ScenarioService
from elaborations.services.alembic.scenario_step_service import ScenarioStepService
from elaborations.services.alembic.step_operation_service import StepOperationService
from elaborations.services.scenarios.scenario_executor_service import (
    execute_scenario_by_id,
    execute_scenario_step_by_id,
)
from exceptions.app_exception import QsmithAppException

router = APIRouter(prefix="/elaborations")


def _insert_step_operations(
    session,
    scenario_step_id: str,
    operations: list[CreateStepOperationDto],
):
    for operation in operations or []:
        op_entity = StepOperationEntity()
        op_entity.order = operation.order
        op_entity.scenario_step_id = scenario_step_id
        op_entity.operation_id = operation.operation_id
        StepOperationService().insert(session, op_entity)


def _insert_scenario_steps(
    session,
    scenario_id: str,
    steps: list[CreateScenarioStepDto],
):
    for step in steps or []:
        scenario_step_entity = ScenarioStepEntity()
        scenario_step_entity.order = step.order
        scenario_step_entity.scenario_id = scenario_id
        scenario_step_entity.step_id = step.step_id
        scenario_step_entity.description = step.description
        scenario_step_entity.on_failure = step.on_failure
        scenario_step_id = ScenarioStepService().insert(session, scenario_step_entity)
        _insert_step_operations(session, scenario_step_id, step.operations or [])


@router.post("/scenario")
async def insert_scenario_api(scenario_dto: CreateScenarioDto):
    with managed_session() as session:
        scenario_entity = ScenarioEntity()
        scenario_entity.code = scenario_dto.code
        scenario_entity.description = scenario_dto.description
        scenario_id = ScenarioService().insert(session, scenario_entity)
        _insert_scenario_steps(session, scenario_id, scenario_dto.steps or [])
    return {"id": scenario_id, "message": "Scenario added"}


@router.put("/scenario")
async def update_scenario_api(scenario_dto: UpdateScenarioDto):
    with managed_session() as session:
        scenario_entity = ScenarioService().update(
            session,
            scenario_dto.id,
            code=scenario_dto.code,
            description=scenario_dto.description,
        )
        if not scenario_entity:
            raise QsmithAppException(f"No scenario found with id [ {scenario_dto.id} ]")

        ScenarioStepService().delete_by_scenario_id(session, scenario_dto.id)
        _insert_scenario_steps(session, scenario_dto.id, scenario_dto.steps or [])

    return {"id": scenario_dto.id, "message": "Scenario updated"}


@router.get("/scenario")
async def find_all_scenarios_api():
    with managed_session() as session:
        all = ScenarioService().get_all(session)
        results = []
        for scenario in all:
            results.append({
                "id": scenario.id,
                "code": scenario.code,
                "description": scenario.description
            })
        return results


@router.get("/scenario/{_id}")
async def find_scenario_api(_id: str):
    with managed_session() as session:
        scenario = ScenarioService().get_by_id(session, _id)
        if not scenario:
            raise QsmithAppException(f"No scenario found with id [ {_id} ]")

        scenario_steps = ScenarioStepService().get_all_by_scenario_id(session, _id)
        result_steps = []
        for scenario_step in scenario_steps:
            step_operations = StepOperationService().get_all_by_step(session, scenario_step.id)
            result_operations = []
            for step_operation in step_operations:
                result_operations.append(
                    {
                        "id": step_operation.id,
                        "scenario_step_id": step_operation.scenario_step_id,
                        "operation_id": step_operation.operation_id,
                        "order": step_operation.order,
                    }
                )

            result_steps.append(
                {
                    "id": scenario_step.id,
                    "scenario_id": scenario_step.scenario_id,
                    "step_id": scenario_step.step_id,
                    "description": scenario_step.description,
                    "order": scenario_step.order,
                    "on_failure": scenario_step.on_failure,
                    "operations": result_operations,
                }
            )

        return {
            "id": scenario.id,
            "code": scenario.code,
            "description": scenario.description,
            "steps": result_steps,
        }


@router.delete("/scenario/{_id}")
async def delete_scenario_api(_id: str):
    with managed_session() as session:
        result = ScenarioService().delete_by_id(session, _id)
        if result == 0:
            raise QsmithAppException(f"No scenario found with id [ {_id} ]")
        return {"message": f"{result} scenario(s) deleted"}


@router.get("/scenario/{_id}/execute")
async def execute_scenario_api(_id):
    execution_id = execute_scenario_by_id(_id)
    return {"message": "Scenario started", "execution_id": execution_id}


@router.post("/scenario/{scenario_id}/step/{scenario_step_id}/execute")
async def execute_scenario_step_api(
    scenario_id: str,
    scenario_step_id: str,
    dto: ExecuteScenarioStepDto,
):
    execution_id = execute_scenario_step_by_id(
        scenario_id=scenario_id,
        scenario_step_id=scenario_step_id,
        include_previous=dto.include_previous,
    )
    return {"message": "Scenario step started", "execution_id": execution_id}
