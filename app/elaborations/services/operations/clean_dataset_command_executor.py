from sqlalchemy import text
from sqlalchemy.orm import Session

from _alembic.models.json_payload_entity import JsonPayloadEntity
from data_sources.models.database_connection_config_types import DatabaseConnectionConfigTypes
from data_sources.services.alembic.database_connection_service import load_database_connection
from elaborations.models.dtos.configuration_command_dto import (
    CleanDatasetConfigurationCommandDto,
)
from elaborations.services.operations.command_executor import (
    ExecutionResultDto,
    OperationExecutor,
)
from json_utils.models.enums.json_type import JsonType
from json_utils.services.alembic.json_files_service import JsonFilesService
from sqlalchemy_utils.engine_factory.sqlalchemy_engine_factory_composite import (
    create_sqlalchemy_engine,
)


class CleanDatasetOperationExecutor(OperationExecutor):
    def execute(
        self,
        session: Session,
        operation_id: str,
        cfg: CleanDatasetConfigurationCommandDto,
        data,
    ) -> ExecutionResultDto:
        entity: JsonPayloadEntity = JsonFilesService().get_by_id(session, cfg.dataset_id)
        if not entity or entity.json_type != JsonType.DATABASE_TABLE.value:
            raise ValueError(f"Database datasource '{cfg.dataset_id}' not found")
        payload = entity.payload if isinstance(entity.payload, dict) else {}
        connection_id = str(payload.get("connection_id") or "").strip()
        table_name = self._table_name_from_payload(payload)
        database_connection_cfg: DatabaseConnectionConfigTypes = load_database_connection(connection_id)
        engine = create_sqlalchemy_engine(database_connection_cfg)
        with engine.begin() as connection:
            connection.execute(text(f"DELETE FROM {table_name}"))
        message = f"Cleaned dataset '{cfg.dataset_id}' table '{table_name}'."
        self.log(operation_id, message)
        return ExecutionResultDto(data=data, result=[{"message": message, "dataset_id": cfg.dataset_id}])

    @staticmethod
    def _table_name_from_payload(payload: dict) -> str:
        object_name = str(payload.get("object_name") or "").strip()
        schema = str(payload.get("schema") or "").strip()
        return object_name if not schema or "." in object_name else f"{schema}.{object_name}"

