from fastapi import APIRouter

from _alembic.models.scenario_step_entity import ScenarioStepEntity
from _alembic.services.session_context_manager import managed_session
from elaborations.models.dtos.create_scenario_dto import CreateScenarioStepDto
from elaborations.services.alembic.scenario_step_service import ScenarioStepService
from exceptions.app_exception import QsmithAppException

router = APIRouter(prefix="/elaborations")


@router.get("/scenario/{scenario_id}/step")
async def find_all_by_scenario_api(scenario_id:str):
    with managed_session() as session:
        all = ScenarioStepService().get_all_by_scenario_id(session,scenario_id)
        results = []
        for step in all:
            results.append({
                "id": step.id,
                "scenario_id": step.scenario_id,
                "step_id": step.step_id,
                "code": step.step_id,
                "description": step.description,
                "order": step.order,
                "on_failure": step.on_failure
            })
        return results


@router.put("/scenario/{scenario_id}/step")
async def insert_scenario_step_api(scenario_id: str, dto:CreateScenarioStepDto):
    with managed_session() as session:
        entity = ScenarioStepEntity()
        entity.scenario_id = scenario_id
        entity.step_id = dto.step_id
        entity.description = dto.description
        entity.on_failure = dto.on_failure
        entity.order = dto.order
        scenario_step_id = ScenarioStepService().insert(session,entity)
        return {"id": scenario_step_id, "message": "Scenario step added"}


@router.delete("/scenario/{scenario_id}/step")
async def delete_scenario_step_api(scenario_id: str):
    with managed_session() as session:
        result = ScenarioStepService().delete_by_scenario_id(session, scenario_id)
        if result == 0:
            raise QsmithAppException(f"No scenario steps found with scenario id [ {scenario_id} ]")
        return {"message": f"{result} scenario step(s) deleted"}

