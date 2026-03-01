from fastapi import APIRouter

from _alembic.models.scenario_step_entity import ScenarioStepEntity
from _alembic.services.session_context_manager import managed_session
from elaborations.models.dtos.create_scenario_dto import CreateScenarioStepDto
from elaborations.models.enums.on_failure import OnFailure
from elaborations.services.alembic.scenario_step_service import ScenarioStepService
from elaborations.services.alembic.step_service import StepService
from exceptions.app_exception import QsmithAppException

router = APIRouter(prefix="/elaborations")


def _normalize_on_failure(value: str | None) -> str:
    normalized = str(value or OnFailure.ABORT.value).strip().upper()
    if normalized not in {OnFailure.ABORT.value, OnFailure.CONTINUE.value}:
        return OnFailure.ABORT.value
    return normalized


def _build_scenario_step_entity(session, scenario_id: str, dto: CreateScenarioStepDto) -> ScenarioStepEntity:
    entity = ScenarioStepEntity()
    entity.scenario_id = scenario_id
    entity.order = dto.order
    entity.on_failure = _normalize_on_failure(dto.on_failure)

    dto_cfg = dto.cfg.model_dump() if dto.cfg else None
    dto_step_type = str((dto.cfg.stepType if dto.cfg else None) or dto.step_type or "").strip()

    step_id = str(dto.step_id or "").strip()
    if step_id:
        source_step = StepService().get_by_id(session, step_id)
        if not source_step:
            raise QsmithAppException(f"No step found with id [ {step_id} ]")
        entity.code = str(dto.code or source_step.code or "").strip()
        entity.description = (
            str(dto.description)
            if dto.description is not None and str(dto.description).strip()
            else str(source_step.description or "")
        )
        entity.step_type = str(dto_step_type or source_step.step_type or "").strip()
        entity.configuration_json = (
            dto_cfg
            if isinstance(dto_cfg, dict)
            else (source_step.configuration_json if isinstance(source_step.configuration_json, dict) else {})
        )
    else:
        entity.code = str(dto.code or "").strip()
        entity.description = str(dto.description or "")
        entity.step_type = dto_step_type
        entity.configuration_json = dto_cfg if isinstance(dto_cfg, dict) else {}

    if not entity.code:
        raise QsmithAppException("Step code is required.")
    if not entity.step_type:
        raise QsmithAppException("Step type is required.")

    return entity


@router.get("/scenario/{scenario_id}/step")
async def find_all_by_scenario_api(scenario_id: str):
    with managed_session() as session:
        all_steps = ScenarioStepService().get_all_by_scenario_id(session, scenario_id)
        results = []
        for step in all_steps:
            results.append(
                {
                    "id": step.id,
                    "scenario_id": step.scenario_id,
                    "code": step.code,
                    "description": step.description,
                    "step_type": step.step_type,
                    "configuration_json": step.configuration_json,
                    "order": step.order,
                    "on_failure": step.on_failure,
                }
            )
        return results


@router.put("/scenario/{scenario_id}/step")
async def insert_scenario_step_api(scenario_id: str, dto: CreateScenarioStepDto):
    with managed_session() as session:
        entity = _build_scenario_step_entity(session, scenario_id, dto)
        scenario_step_id = ScenarioStepService().insert(session, entity)
        return {"id": scenario_step_id, "message": "Scenario step added"}


@router.delete("/scenario/{scenario_id}/step")
async def delete_scenario_step_api(scenario_id: str):
    with managed_session() as session:
        result = ScenarioStepService().delete_by_scenario_id(session, scenario_id)
        if result == 0:
            raise QsmithAppException(f"No scenario steps found with scenario id [ {scenario_id} ]")
        return {"message": f"{result} scenario step(s) deleted"}
