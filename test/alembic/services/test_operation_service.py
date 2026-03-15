from app._alembic.models.operation_entity import OperationEntity
from app._alembic.services.session_context_manager import managed_session
from app.elaborations.models.enums.operation_type import OperationType
from app.elaborations.services.alembic.operation_service import OperationService

entity = OperationEntity(
    code="operation_1",
    operation_type=OperationType.PUBLISH.value,
    configuration_json={"key": "value"}
)

def test_operations_service(alembic_container):
    new_id = _verify_insert_entity()
    _verify_update_entity(new_id)
    _verify_delete_entity(new_id)

def _verify_insert_entity()->str:
    with managed_session() as session:
        service = OperationService()

        inserted_id = service.insert(session, entity)

        retrieved_entity = service.get_by_id(session, inserted_id)

        assert retrieved_entity is not None
        assert retrieved_entity.operation_type == OperationType.PUBLISH.value
        assert retrieved_entity.configuration_json == {"key": "value"}

        return inserted_id

def _verify_update_entity(_id:str):
    with managed_session() as session:
        service = OperationService()

        updated_entity = service.update(
            session,
            _id,
            operation_type=OperationType.SAVE_EXTERNAL_DB.value,
            configuration_json={"new_key": "new_value"}
        )

        assert updated_entity.operation_type == OperationType.SAVE_EXTERNAL_DB.value
        assert updated_entity.configuration_json == {"new_key": "new_value"}


def _verify_delete_entity(_id:str):
    with managed_session() as session:
        service = OperationService()

        delete_count = service.delete_by_id(session, _id)
        assert delete_count == 1

        retrieved_entity = service.get_by_id(session, _id)
        assert retrieved_entity is None

