import math

from fastapi import APIRouter, Query

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
async def find_all_step_api(
    page: int | None = Query(default=None, ge=1),
    size: int = Query(default=5, ge=1),
    search: str | None = Query(default=None),
):
    with managed_session() as session:
        service = StepService()
        query = service.get_filtered_query(session, search or "")

        if page is None:
            steps = query.all()
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

        total_items = query.count()
        total_pages = math.ceil(total_items / size) if total_items > 0 else 0
        offset = (page - 1) * size
        steps = query.offset(offset).limit(size).all()

        items = []
        for step in steps:
            items.append({
                "id": step.id,
                "code": step.code,
                "description": step.description,
                "step_type": step.step_type,
                "configuration_json": step.configuration_json
            })

        return {
            "items": items,
            "page": page,
            "size": size,
            "total_items": total_items,
            "total_pages": total_pages,
        }

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


