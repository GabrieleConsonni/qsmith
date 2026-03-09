from fastapi import APIRouter, Query

from _alembic.models.scenario_execution_entity import ScenarioExecutionEntity
from _alembic.models.scenario_step_execution_entity import ScenarioStepExecutionEntity
from _alembic.models.step_operation_execution_entity import StepOperationExecutionEntity
from _alembic.services.session_context_manager import managed_session
from elaborations.services.alembic.scenario_execution_service import ScenarioExecutionService
from elaborations.services.alembic.scenario_step_execution_service import (
    ScenarioStepExecutionService,
)
from elaborations.services.alembic.step_operation_execution_service import (
    StepOperationExecutionService,
)
from exceptions.app_exception import QsmithAppException

router = APIRouter(prefix="/elaborations")


def _serialize_operation_execution(entity: StepOperationExecutionEntity) -> dict:
    return {
        "id": entity.id,
        "scenario_execution_id": entity.scenario_execution_id,
        "scenario_step_execution_id": entity.scenario_step_execution_id,
        "scenario_step_id": entity.scenario_step_id,
        "step_operation_id": entity.step_operation_id,
        "operation_code": entity.operation_code,
        "operation_description": entity.operation_description,
        "operation_order": int(entity.operation_order),
        "status": entity.status,
        "error_message": entity.error_message,
        "started_at": entity.started_at,
        "finished_at": entity.finished_at,
    }


def _serialize_step_execution(
    session,
    entity: ScenarioStepExecutionEntity,
    step_operation_execution_service: StepOperationExecutionService,
) -> dict:
    operations = step_operation_execution_service.get_all_by_step_execution_id(session, entity.id)
    return {
        "id": entity.id,
        "scenario_execution_id": entity.scenario_execution_id,
        "scenario_step_id": entity.scenario_step_id,
        "step_code": entity.step_code,
        "step_description": entity.step_description,
        "step_order": int(entity.step_order),
        "status": entity.status,
        "error_message": entity.error_message,
        "started_at": entity.started_at,
        "finished_at": entity.finished_at,
        "operations": [_serialize_operation_execution(operation) for operation in operations],
    }


def _serialize_scenario_execution(
    session,
    entity: ScenarioExecutionEntity,
    scenario_step_execution_service: ScenarioStepExecutionService,
    step_operation_execution_service: StepOperationExecutionService,
) -> dict:
    step_executions = scenario_step_execution_service.get_all_by_execution_id(session, entity.id)
    return {
        "id": entity.id,
        "scenario_id": entity.scenario_id,
        "scenario_code": entity.scenario_code,
        "scenario_description": entity.scenario_description,
        "status": entity.status,
        "invocation_id": entity.invocation_id,
        "vars_init_json": entity.vars_init_json,
        "result_json": entity.result_json,
        "include_previous": bool(entity.include_previous),
        "requested_step_id": entity.requested_step_id,
        "requested_step_code": entity.requested_step_code,
        "error_message": entity.error_message,
        "started_at": entity.started_at,
        "finished_at": entity.finished_at,
        "steps": [
            _serialize_step_execution(session, step_execution, step_operation_execution_service)
            for step_execution in step_executions
        ],
    }


@router.get("/scenario-execution")
async def find_all_scenario_executions_api(
    scenario_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
):
    with managed_session() as session:
        scenario_execution_service = ScenarioExecutionService()
        scenario_step_execution_service = ScenarioStepExecutionService()
        step_operation_execution_service = StepOperationExecutionService()

        scenario_id_value = str(scenario_id or "").strip()
        if scenario_id_value:
            executions = scenario_execution_service.get_all_by_scenario_id(
                session=session,
                scenario_id=scenario_id_value,
                limit=limit,
            )
        else:
            executions = scenario_execution_service.get_all_ordered(
                session=session,
                limit=limit,
            )

        return [
            _serialize_scenario_execution(
                session,
                execution,
                scenario_step_execution_service,
                step_operation_execution_service,
            )
            for execution in executions
        ]


@router.get("/scenario-execution/{execution_id}")
async def find_scenario_execution_by_id_api(execution_id: str):
    with managed_session() as session:
        scenario_execution_service = ScenarioExecutionService()
        scenario_step_execution_service = ScenarioStepExecutionService()
        step_operation_execution_service = StepOperationExecutionService()
        execution = scenario_execution_service.get_by_id(session, execution_id)
        if not execution:
            raise QsmithAppException(f"No scenario execution found with id [ {execution_id} ]")

        return _serialize_scenario_execution(
            session,
            execution,
            scenario_step_execution_service,
            step_operation_execution_service,
        )


@router.delete("/scenario-execution/{execution_id}")
async def delete_scenario_execution_by_id_api(execution_id: str):
    with managed_session() as session:
        deleted = ScenarioExecutionService().delete_by_id(session, execution_id)
        if deleted == 0:
            raise QsmithAppException(f"No scenario execution found with id [ {execution_id} ]")
        return {"message": f"{deleted} scenario execution(s) deleted"}
