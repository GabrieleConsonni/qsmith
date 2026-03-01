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
from elaborations.models.enums.on_failure import OnFailure
from elaborations.services.alembic.operation_service import OperationService
from elaborations.services.alembic.scenario_service import ScenarioService
from elaborations.services.alembic.scenario_step_service import ScenarioStepService
from elaborations.services.alembic.step_operation_service import StepOperationService
from elaborations.services.alembic.step_service import StepService
from elaborations.services.scenarios.scenario_executor_service import (
    execute_scenario_by_id,
    execute_scenario_step_by_id,
)
from exceptions.app_exception import QsmithAppException

router = APIRouter(prefix="/elaborations")


def _normalize_on_failure(value: str | None) -> str:
    normalized = str(value or OnFailure.ABORT.value).strip().upper()
    if normalized not in {OnFailure.ABORT.value, OnFailure.CONTINUE.value}:
        return OnFailure.ABORT.value
    return normalized


def _build_step_operation_entity(session, dto: CreateStepOperationDto) -> StepOperationEntity:
    operation_entity = StepOperationEntity()
    operation_entity.order = dto.order

    dto_cfg = dto.cfg.model_dump() if dto.cfg else None
    dto_type = str((dto.cfg.operationType if dto.cfg else None) or "").strip()

    operation_id = str(dto.operation_id or "").strip()
    if operation_id:
        source_operation = OperationService().get_by_id(session, operation_id)
        if not source_operation:
            raise QsmithAppException(f"No operation found with id [ {operation_id} ]")

        operation_entity.code = str(dto.code or source_operation.code or "").strip()
        if not operation_entity.code:
            raise QsmithAppException("Operation code is required.")

        operation_entity.description = (
            str(dto.description)
            if dto.description is not None and str(dto.description).strip()
            else str(source_operation.description or "")
        )
        operation_entity.operation_type = str(dto_type or source_operation.operation_type or "").strip()
        operation_entity.configuration_json = (
            dto_cfg
            if isinstance(dto_cfg, dict)
            else (
                source_operation.configuration_json
                if isinstance(source_operation.configuration_json, dict)
                else {}
            )
        )
    else:
        operation_entity.code = str(dto.code or "").strip()
        operation_entity.description = str(dto.description or "")
        operation_entity.operation_type = dto_type
        operation_entity.configuration_json = dto_cfg if isinstance(dto_cfg, dict) else {}

    if not operation_entity.code:
        raise QsmithAppException("Operation code is required.")
    if not operation_entity.operation_type:
        raise QsmithAppException("Operation type is required.")

    return operation_entity


def _build_scenario_step_entity(session, scenario_id: str, dto: CreateScenarioStepDto) -> ScenarioStepEntity:
    step_entity = ScenarioStepEntity()
    step_entity.scenario_id = scenario_id
    step_entity.order = dto.order
    step_entity.on_failure = _normalize_on_failure(dto.on_failure)

    dto_cfg = dto.cfg.model_dump() if dto.cfg else None
    dto_step_type = str((dto.cfg.stepType if dto.cfg else None) or dto.step_type or "").strip()

    step_id = str(dto.step_id or "").strip()
    if step_id:
        source_step = StepService().get_by_id(session, step_id)
        if not source_step:
            raise QsmithAppException(f"No step found with id [ {step_id} ]")

        step_entity.code = str(dto.code or source_step.code or "").strip()
        step_entity.description = (
            str(dto.description)
            if dto.description is not None and str(dto.description).strip()
            else str(source_step.description or "")
        )
        step_entity.step_type = str(dto_step_type or source_step.step_type or "").strip()
        step_entity.configuration_json = (
            dto_cfg
            if isinstance(dto_cfg, dict)
            else (source_step.configuration_json if isinstance(source_step.configuration_json, dict) else {})
        )
    else:
        step_entity.code = str(dto.code or "").strip()
        step_entity.description = str(dto.description or "")
        step_entity.step_type = dto_step_type
        step_entity.configuration_json = dto_cfg if isinstance(dto_cfg, dict) else {}

    if not step_entity.code:
        raise QsmithAppException("Step code is required.")
    if not step_entity.step_type:
        raise QsmithAppException("Step type is required.")

    return step_entity


def _insert_step_operations(
    session,
    scenario_step_id: str,
    operations: list[CreateStepOperationDto],
):
    for operation in operations or []:
        op_entity = _build_step_operation_entity(session, operation)
        op_entity.scenario_step_id = scenario_step_id
        StepOperationService().insert(session, op_entity)


def _insert_scenario_steps(
    session,
    scenario_id: str,
    steps: list[CreateScenarioStepDto],
):
    for step in steps or []:
        scenario_step_entity = _build_scenario_step_entity(session, scenario_id, step)
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
        all_scenarios = ScenarioService().get_all(session)
        results = []
        for scenario in all_scenarios:
            results.append({
                "id": scenario.id,
                "code": scenario.code,
                "description": scenario.description,
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
                        "code": step_operation.code,
                        "description": step_operation.description,
                        "operation_type": step_operation.operation_type,
                        "configuration_json": step_operation.configuration_json,
                        "order": step_operation.order,
                    }
                )

            result_steps.append(
                {
                    "id": scenario_step.id,
                    "scenario_id": scenario_step.scenario_id,
                    "code": scenario_step.code,
                    "description": scenario_step.description,
                    "step_type": scenario_step.step_type,
                    "configuration_json": scenario_step.configuration_json,
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
