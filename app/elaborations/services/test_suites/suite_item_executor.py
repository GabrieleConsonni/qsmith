from sqlalchemy.orm import Session

from _alembic.models.suite_item_entity import SuiteItemEntity
from elaborations.services.alembic.suite_item_operation_service import (
    SuiteItemOperationService,
)
from elaborations.services.operations.operation_executor_composite import execute_operations
from elaborations.services.scenarios.execution_runtime_context import bind_execution_context
from elaborations.services.scenarios.run_context import set_context_last


def execute_suite_item(session: Session, suite_item: SuiteItemEntity) -> list[dict[str, object]]:
    operations = SuiteItemOperationService().get_all_by_suite_item_id(session, suite_item.id)
    with bind_execution_context(suite_item_id=suite_item.id):
        execution_result = execute_operations(session, operations, [])
    set_context_last(str(suite_item.code or suite_item.id), execution_result.data)
    return execution_result.result
