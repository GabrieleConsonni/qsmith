import math

from fastapi import APIRouter, Query

from _alembic.models.operation_entity import OperationEntity
from _alembic.services.session_context_manager import managed_session
from elaborations.models.dtos.create_operation_dto import CreateOperationDto
from elaborations.services.alembic.operation_service import OperationService
from exceptions.app_exception import QsmithAppException

router = APIRouter(prefix="/elaborations")

@router.post("/operation")
async def insert_operation_api(dto:CreateOperationDto):
    with managed_session() as session:
        entity = OperationEntity()
        entity.code = dto.code
        entity.description = dto.description
        entity.operation_type = dto.cfg.operationType
        entity.configuration_json = dto.cfg.model_dump()
        op_id = OperationService().insert(
            session,
            entity
        )
    return {"id":op_id, "message": "Operation added"}


@router.get("/operation")
async def find_all_operation_api(
    page: int | None = Query(default=None, ge=1),
    size: int = Query(default=5, ge=1),
    search: str | None = Query(default=None),
):
    with managed_session() as session:
        service = OperationService()
        query = service.get_filtered_query(session, search or "")

        if page is None:
            ops = query.all()
            result = []
            for op in ops:
                result.append({
                    "id": op.id,
                    "code": op.code,
                    "description": op.description,
                    "operation_type": op.operation_type,
                    "configuration_json": op.configuration_json
                })
            return result

        total_items = query.count()
        total_pages = math.ceil(total_items / size) if total_items > 0 else 0
        offset = (page - 1) * size
        ops = query.offset(offset).limit(size).all()

        items = []
        for op in ops:
            items.append({
                "id": op.id,
                "code": op.code,
                "description": op.description,
                "operation_type": op.operation_type,
                "configuration_json": op.configuration_json
            })

        return {
            "items": items,
            "page": page,
            "size": size,
            "total_items": total_items,
            "total_pages": total_pages,
        }


@router.get("/operation/{_id}")
async def find_operation_by_id_api(_id:str):
    with managed_session() as session:
        op = OperationService().get_by_id(session, _id)
        if not op:
            raise QsmithAppException(f"No Operation found with id [ {_id} ]")
        return {
                "id": op.id,
                "code": op.code,
                "description": op.description,
                "operation_type": op.operation_type,
                "configuration_json": op.configuration_json
            }


@router.delete("/operation/{_id}")
async def delete_operation_by_id_api(_id: str):
    with managed_session() as session:
        result = OperationService().delete_by_id(session, _id)
        if result == 0:
            raise QsmithAppException(f"No Operation found with id [ {_id} ]")
        return {"message": f"{result} Operation(s) deleted"}


