from fastapi import APIRouter

from _alembic.models.suite_item_entity import SuiteItemEntity
from _alembic.models.suite_item_operation_entity import SuiteItemOperationEntity
from _alembic.models.test_suite_entity import TestSuiteEntity
from _alembic.services.session_context_manager import managed_session
from elaborations.models.dtos.execute_scenario_step_dto import ExecuteScenarioStepDto
from elaborations.models.dtos.test_suite_dto import (
    CreateSuiteItemDto,
    CreateSuiteItemOperationDto,
    CreateTestSuiteDto,
    UpdateTestSuiteDto,
)
from elaborations.models.enums.hook_phase import HookPhase
from elaborations.models.enums.on_failure import OnFailure
from elaborations.models.enums.suite_item_kind import SuiteItemKind
from elaborations.services.alembic.operation_service import OperationService
from elaborations.services.alembic.suite_item_operation_service import (
    SuiteItemOperationService,
)
from elaborations.services.alembic.suite_item_service import SuiteItemService
from elaborations.services.alembic.test_suite_service import TestSuiteService
from elaborations.services.test_suites.test_suite_executor_service import (
    execute_test_by_id,
    execute_test_suite_by_id,
)
from exceptions.app_exception import QsmithAppException

router = APIRouter(prefix="/elaborations")


def _normalize_on_failure(value: str | None) -> str:
    normalized = str(value or OnFailure.ABORT.value).strip().upper()
    if normalized not in {OnFailure.ABORT.value, OnFailure.CONTINUE.value}:
        return OnFailure.ABORT.value
    return normalized


def _build_suite_item_operation_entity(session, dto: CreateSuiteItemOperationDto) -> SuiteItemOperationEntity:
    entity = SuiteItemOperationEntity()
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


def _build_suite_item_entity(test_suite_id: str, dto: CreateSuiteItemDto, position: int) -> SuiteItemEntity:
    entity = SuiteItemEntity()
    entity.test_suite_id = test_suite_id
    entity.kind = str(dto.kind or SuiteItemKind.TEST.value)
    entity.hook_phase = str(dto.hook_phase or "").strip() or None
    entity.code = str(dto.code or "").strip()
    entity.description = str(dto.description or "")
    entity.position = position
    entity.on_failure = _normalize_on_failure(dto.on_failure)
    return entity


def _insert_suite_item_operations(session, suite_item_id: str, operations: list[CreateSuiteItemOperationDto]):
    for operation in operations or []:
        entity = _build_suite_item_operation_entity(session, operation)
        entity.suite_item_id = suite_item_id
        SuiteItemOperationService().insert(session, entity)


def _insert_suite_items(
    session,
    test_suite_id: str,
    *,
    hooks: list[CreateSuiteItemDto],
    tests: list[CreateSuiteItemDto],
):
    seen_hook_phases: set[str] = set()
    for phase in HookPhase:
        hook = next(
            (
                item
                for item in hooks or []
                if str(item.hook_phase or "").strip().lower() == phase.value
            ),
            None,
        )
        if hook is None:
            continue
        if phase.value in seen_hook_phases:
            raise QsmithAppException(f"Duplicate hook for phase '{phase.value}'.")
        seen_hook_phases.add(phase.value)
        suite_item_entity = _build_suite_item_entity(test_suite_id, hook, position=0)
        suite_item_id = SuiteItemService().insert(session, suite_item_entity)
        _insert_suite_item_operations(session, suite_item_id, hook.operations or [])

    for position, test in enumerate(tests or [], start=1):
        suite_item_entity = _build_suite_item_entity(test_suite_id, test, position=position)
        suite_item_id = SuiteItemService().insert(session, suite_item_entity)
        _insert_suite_item_operations(session, suite_item_id, test.operations or [])


def _serialize_operation(operation: SuiteItemOperationEntity) -> dict:
    return {
        "id": operation.id,
        "suite_item_id": operation.suite_item_id,
        "code": operation.code,
        "description": operation.description,
        "operation_type": operation.operation_type,
        "configuration_json": operation.configuration_json,
        "order": int(operation.order),
    }


def _serialize_item(session, item: SuiteItemEntity) -> dict:
    operations = SuiteItemOperationService().get_all_by_suite_item_id(session, item.id)
    return {
        "id": item.id,
        "test_suite_id": item.test_suite_id,
        "kind": item.kind,
        "hook_phase": item.hook_phase,
        "code": item.code,
        "description": item.description,
        "position": int(item.position),
        "on_failure": item.on_failure,
        "operations": [_serialize_operation(operation) for operation in operations],
    }


@router.post("/test-suite")
async def insert_test_suite_api(dto: CreateTestSuiteDto):
    with managed_session() as session:
        entity = TestSuiteEntity()
        entity.code = dto.code
        entity.description = dto.description
        test_suite_id = TestSuiteService().insert(session, entity)
        _insert_suite_items(session, test_suite_id, hooks=dto.hooks or [], tests=dto.tests or [])
    return {"id": test_suite_id, "message": "Test suite added"}


@router.put("/test-suite")
async def update_test_suite_api(dto: UpdateTestSuiteDto):
    with managed_session() as session:
        entity = TestSuiteService().update(session, dto.id, code=dto.code, description=dto.description)
        if not entity:
            raise QsmithAppException(f"No test suite found with id [ {dto.id} ]")
        SuiteItemService().delete_by_suite_id(session, dto.id)
        _insert_suite_items(session, dto.id, hooks=dto.hooks or [], tests=dto.tests or [])
    return {"id": dto.id, "message": "Test suite updated"}


@router.get("/test-suite")
async def find_all_test_suites_api():
    with managed_session() as session:
        return [
            {"id": suite.id, "code": suite.code, "description": suite.description}
            for suite in TestSuiteService().get_all(session)
        ]


@router.get("/test-suite/{_id}")
async def find_test_suite_api(_id: str):
    with managed_session() as session:
        suite = TestSuiteService().get_by_id(session, _id)
        if not suite:
            raise QsmithAppException(f"No test suite found with id [ {_id} ]")
        items = SuiteItemService().get_all_by_suite_id(session, _id)
        hooks = []
        tests = []
        for item in items:
            serialized = _serialize_item(session, item)
            if str(item.kind or "") == SuiteItemKind.HOOK.value:
                hooks.append(serialized)
            else:
                tests.append(serialized)
        return {
            "id": suite.id,
            "code": suite.code,
            "description": suite.description,
            "hooks": hooks,
            "tests": tests,
        }


@router.delete("/test-suite/{_id}")
async def delete_test_suite_api(_id: str):
    with managed_session() as session:
        result = TestSuiteService().delete_by_id(session, _id)
        if result == 0:
            raise QsmithAppException(f"No test suite found with id [ {_id} ]")
        return {"message": f"{result} test suite(s) deleted"}


@router.get("/test-suite/{_id}/execute")
async def execute_test_suite_api(_id: str):
    execution_id = execute_test_suite_by_id(_id)
    return {"message": "Test suite started", "execution_id": execution_id}


@router.post("/test-suite/{test_suite_id}/test/{suite_item_id}/execute")
async def execute_test_api(test_suite_id: str, suite_item_id: str, dto: ExecuteScenarioStepDto):
    execution_id = execute_test_by_id(
        test_suite_id=test_suite_id,
        suite_item_id=suite_item_id,
        include_previous=dto.include_previous,
    )
    return {"message": "Test started", "execution_id": execution_id}
