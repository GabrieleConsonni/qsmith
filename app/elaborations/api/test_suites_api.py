from fastapi import APIRouter

from _alembic.models.suite_item_entity import SuiteItemEntity
from _alembic.models.suite_item_command_entity import SuiteItemOperationEntity
from _alembic.models.test_suite_entity import TestSuiteEntity
from _alembic.services.session_context_manager import managed_session
from elaborations.models.dtos.send_message_template_preview_dto import (
    PreviewSendMessageTemplateRowsDto,
)
from elaborations.models.dtos.test_suite_dto import (
    CreateSuiteItemDto,
    CreateSuiteItemCommandDto,
    CreateTestSuiteDto,
    UpdateTestSuiteDto,
)
from elaborations.models.enums.hook_phase import HookPhase
from elaborations.models.enums.on_failure import OnFailure
from elaborations.models.enums.suite_item_kind import SuiteItemKind
from elaborations.services.alembic.suite_item_command_service import (
    SuiteItemOperationService,
)
from elaborations.services.alembic.suite_item_service import SuiteItemService
from elaborations.services.alembic.test_suite_service import TestSuiteService
from elaborations.services.constants.command_constant_definition_registry import (
    rebuild_suite_constant_definitions,
    validate_suite_constant_graph,
)
from elaborations.services.operations.send_message_template_service import (
    preview_send_message_template_rows,
)
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


def _build_suite_item_command_entity(dto: CreateSuiteItemCommandDto) -> SuiteItemOperationEntity:
    entity = SuiteItemOperationEntity()
    entity.order = dto.order
    dto_cfg = dto.cfg.model_dump() if dto.cfg else None
    dto_type = str((dto.cfg.commandCode if dto.cfg else None) or "").strip()
    dto_family = str((dto.cfg.commandType if dto.cfg else None) or "").strip()
    entity.description = str(dto.description or "")
    entity.operation_type = dto_type
    if hasattr(entity, "command_code"):
        entity.command_code = dto_type
    if hasattr(entity, "command_type"):
        entity.command_type = dto_family
    entity.configuration_json = dto_cfg if isinstance(dto_cfg, dict) else {}

    if not dto_type:
        raise QsmithAppException("Command code is required.")
    return entity


def _build_suite_item_entity(test_suite_id: str, dto: CreateSuiteItemDto, position: int) -> SuiteItemEntity:
    entity = SuiteItemEntity()
    entity.test_suite_id = test_suite_id
    entity.kind = str(dto.kind or SuiteItemKind.TEST.value)
    entity.hook_phase = str(dto.hook_phase or "").strip() or None
    entity.description = str(dto.description or "")
    entity.position = position
    entity.on_failure = _normalize_on_failure(dto.on_failure)
    return entity


def _insert_suite_item_operations(session, suite_item_id: str, commands: list[CreateSuiteItemCommandDto]):
    for operation in commands or []:
        entity = _build_suite_item_command_entity(operation)
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
        _insert_suite_item_operations(session, suite_item_id, hook.commands or [])

    for position, test in enumerate(tests or [], start=1):
        suite_item_entity = _build_suite_item_entity(test_suite_id, test, position=position)
        suite_item_id = SuiteItemService().insert(session, suite_item_entity)
        _insert_suite_item_operations(session, suite_item_id, test.commands or [])


def _serialize_operation(operation: SuiteItemOperationEntity) -> dict:
    return {
        "id": operation.id,
        "suite_item_id": operation.suite_item_id,
        "description": operation.description,
        "command_code": getattr(operation, "command_code", None) or operation.operation_type,
        "command_type": getattr(operation, "command_type", None),
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
        "description": item.description,
        "position": int(item.position),
        "on_failure": item.on_failure,
        "commands": [_serialize_operation(operation) for operation in operations],
    }


@router.post("/test-suite")
async def insert_test_suite_api(dto: CreateTestSuiteDto):
    with managed_session() as session:
        validate_suite_constant_graph(dto)
        entity = TestSuiteEntity()
        entity.description = dto.description
        test_suite_id = TestSuiteService().insert(session, entity)
        _insert_suite_items(session, test_suite_id, hooks=dto.hooks or [], tests=dto.tests or [])
        rebuild_suite_constant_definitions(session, test_suite_id)
    return {"id": test_suite_id, "message": "Test suite added"}


@router.put("/test-suite")
async def update_test_suite_api(dto: UpdateTestSuiteDto):
    with managed_session() as session:
        validate_suite_constant_graph(dto)
        entity = TestSuiteService().update(session, dto.id, description=dto.description)
        if not entity:
            raise QsmithAppException(f"No test suite found with id [ {dto.id} ]")
        SuiteItemService().delete_by_suite_id(session, dto.id)
        _insert_suite_items(session, dto.id, hooks=dto.hooks or [], tests=dto.tests or [])
        rebuild_suite_constant_definitions(session, dto.id)
    return {"id": dto.id, "message": "Test suite updated"}


@router.get("/test-suite")
async def find_all_test_suites_api():
    with managed_session() as session:
        return [
            {"id": suite.id, "description": suite.description}
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


@router.post("/test-suite/send-message-template/preview")
async def preview_send_message_template_rows_api(dto: PreviewSendMessageTemplateRowsDto):
    return preview_send_message_template_rows(
        dto.input_data,
        source_type=dto.source_type,
        for_each=dto.for_each,
    )


@router.post("/test-suite/{test_suite_id}/test/{suite_item_id}/execute")
async def execute_test_api(test_suite_id: str, suite_item_id: str):
    execution_id = execute_test_by_id(
        test_suite_id=test_suite_id,
        suite_item_id=suite_item_id,
    )
    return {"message": "Test started", "execution_id": execution_id}

