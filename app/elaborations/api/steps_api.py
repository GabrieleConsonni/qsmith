from fastapi import APIRouter

from _alembic.models.step_entity import StepEntity
from _alembic.services.session_context_manager import managed_session
from elaborations.models.dtos.create_step_dto import CreateStepDto
from elaborations.models.dtos.update_step_dto import UpdateStepDto
from elaborations.services.alembic.step_service import StepService
from exceptions.app_exception import QsmithAppException

router = APIRouter(prefix="/elaborations")

@router.post("/step")
async def insert_step_api(dto:CreateStepDto):
    with managed_session() as session:
        entity = StepEntity()
        entity.code = dto.code
        entity.description = dto.description
        entity.step_type = dto.cfg.stepType
        entity.configuration_json = dto.cfg.model_dump()
        step_id = StepService().insert(
            session,
            entity
        )
    return {"id":step_id, "message": "Step added"}

@router.put("/step")
async def update_step_api(dto:UpdateStepDto):
    with managed_session() as session:
        entity = StepService().update(
            session,
            dto.id,
            code=dto.code,
            description=dto.description,
            step_type=dto.cfg.stepType,
            configuration_json=dto.cfg.model_dump(),
        )
        if not entity:
            raise QsmithAppException(f"No step found with id [ {dto.id} ]")
    return {"id":dto.id, "message": "Step updated"}


@router.get("/step")
async def find_all_step_api():
    with managed_session() as session:
        steps = StepService().get_all(session)
        result = []
        for step in steps:
            result.append({
                "id": step.id,
                "code": step.code,
                "description": step.description,
                "step_type": step.step_type,
                "configuration_json": step.configuration_json
            })
        return result

@router.get("/step/{_id}")
async def find_step_by_id_api(_id:str):
    with managed_session() as session:
        step = StepService().get_by_id(session, _id)
        if not step:
            raise QsmithAppException(f"No step found with id [ {_id} ]")
        return {
                "id": step.id,
                "code": step.code,
                "description": step.description,
                "step_type": step.step_type,
                "configuration_json": step.configuration_json
            }

@router.delete("/step/{_id}")
async def delete_step_by_id_api(_id:str):
    with managed_session() as session:
        step = StepService().get_by_id(session, _id)
        if not step:
            raise QsmithAppException(f"No step found with id [ {_id} ]")
        StepService().delete_by_id(session, _id)
        return {"message": f"Step with id [ {_id} ] deleted successfully"}


