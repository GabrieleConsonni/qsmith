from fastapi import APIRouter

from _alembic.models.step_operation_entity import StepOperationEntity
from _alembic.services.session_context_manager import managed_session
from elaborations.models.dtos.create_scenario_dto import CreateStepOperationDto
from elaborations.services.alembic.operation_service import OperationService
from elaborations.services.alembic.step_operation_service import StepOperationService
from exceptions.app_exception import QsmithAppException

router = APIRouter(prefix="/elaborations")


def _build_step_operation_entity(session, dto: CreateStepOperationDto, scenario_step_id: str) -> StepOperationEntity:
    entity = StepOperationEntity()
    entity.scenario_step_id = scenario_step_id
    entity.order = dto.order

    dto_cfg = dto.cfg.model_dump() if dto.cfg else None
    dto_type = str((dto.cfg.operationType if dto.cfg else None) or "").strip()

    operation_id = str(dto.operation_id or "").strip()
    if operation_id:
        source_operation = OperationService().get_by_id(session, operation_id)
        if not source_operation:
            raise QsmithAppException(f"No operation found with id [ {operation_id} ]")
        entity.code = str(dto.code or source_operation.code or "").strip()
        entity.description = (
            str(dto.description)
            if dto.description is not None and str(dto.description).strip()
            else str(source_operation.description or "")
        )
        entity.operation_type = str(dto_type or source_operation.operation_type or "").strip()
        entity.configuration_json = (
            dto_cfg
            if isinstance(dto_cfg, dict)
            else (
                source_operation.configuration_json
                if isinstance(source_operation.configuration_json, dict)
                else {}
            )
        )
    else:
        entity.code = str(dto.code or "").strip()
        entity.description = str(dto.description or "")
        entity.operation_type = dto_type
        entity.configuration_json = dto_cfg if isinstance(dto_cfg, dict) else {}

    if not entity.code:
        raise QsmithAppException("Operation code is required.")
    if not entity.operation_type:
        raise QsmithAppException("Operation type is required.")

    return entity


@router.get("/scenario/step/{step_id}/operation")
async def find_all_by_step_api(step_id: str):
    with managed_session() as session:
        all_operations = StepOperationService().get_all_by_step(session, step_id)
        results = []
        for operation in all_operations:
            results.append(
                {
                    "id": operation.id,
                    "scenario_step_id": operation.scenario_step_id,
                    "code": operation.code,
                    "description": operation.description,
                    "operation_type": operation.operation_type,
                    "configuration_json": operation.configuration_json,
                    "order": operation.order,
                }
            )
        return results


@router.put("/scenario/step/{step_id}/operation")
async def insert_scenario_step_api(step_id: str, dto: CreateStepOperationDto):
    with managed_session() as session:
        entity = _build_step_operation_entity(session, dto, step_id)
        step_operation_id = StepOperationService().insert(session, entity)
        return {"id": step_operation_id, "message": "Step operation added"}


@router.delete("/scenario/step/{step_id}/operation")
async def delete_step_operations_api(step_id: str):
    with managed_session() as session:
        result = StepOperationService().delete_by_step_id(session, step_id)
        if result == 0:
            raise QsmithAppException(f"No step operations found with step id [ {step_id} ]")
        return {"message": f"{result} step operation(s) deleted"}
