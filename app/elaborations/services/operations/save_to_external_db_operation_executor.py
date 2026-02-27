from sqlalchemy.orm import Session

from _alembic.models.json_payload_entity import JsonPayloadEntity
from data_sources.models.database_connection_config_types import DatabaseConnectionConfigTypes
from data_sources.models.database_connection_config_types import convert_database_connection_config
from elaborations.models.dtos.configuration_operation_dto import SaveToExternalDBConfigurationOperationDto
from elaborations.services.operations.operation_executor import OperationExecutor, ExecutionResultDto
from json_utils.models.enums.json_type import JsonType
from json_utils.services.alembic.json_files_service import JsonFilesService
from sqlalchemy_utils.database_table_writer import DatabaseTableWriter
from sqlalchemy_utils.engine_factory.sqlalchemy_engine_factory_composite import create_sqlalchemy_engine


class SaveToExternalDbOperationExecutor(OperationExecutor):

    def execute(self, session:Session, operation_id:str, cfg: SaveToExternalDBConfigurationOperationDto, data:list[dict])->ExecutionResultDto:
        connection_id = str(cfg.connection_id or "").strip()
        table_name = str(cfg.table_name or "").strip()
        legacy_dataset_id = str(cfg.dataset_id or "").strip()
        if (not connection_id or not table_name) and legacy_dataset_id:
            payload = self.load_database_datasource_payload(session, legacy_dataset_id)
            if not connection_id:
                connection_id = str(payload.get("connection_id") or "").strip()
            if not table_name:
                object_name = str(payload.get("object_name") or "").strip()
                schema = str(payload.get("schema") or "").strip()
                table_name = (
                    object_name if not schema or "." in object_name else f"{schema}.{object_name}"
                )

        if not connection_id:
            raise ValueError("SAVE_EXTERNAL_DB operation requires connection_id.")
        if not table_name:
            raise ValueError("SAVE_EXTERNAL_DB operation requires table_name.")

        connection:DatabaseConnectionConfigTypes = self.load_database_connection(session, connection_id)

        engine = create_sqlalchemy_engine(connection)

        if not data or len(data) == 0:
            message = f"No data to insert into {table_name} table"
            self.log(operation_id, message)
            return ExecutionResultDto(
                data=data,
                result=[{"message": message}]
            )

        sample_row = {}
        for d in data:
            for key, value in d.items():
                sample_row[key] = value


        table = DatabaseTableWriter.ensure_table_exists(engine, table_name, sample_row)
        DatabaseTableWriter.insert_rows(engine, table, data)

        message = f"Created {len(data)} rows in {table_name} table"

        self.log(operation_id, message)

        return ExecutionResultDto(
            data=data,
            result=[{"message": message}]
        )

    def load_database_connection(self,session:Session, _id:str):
        json_payload_entity: JsonPayloadEntity = JsonFilesService().get_by_id(session, _id)

        if not json_payload_entity:
            raise ValueError(f"Database connection '{_id}' not found")

        return convert_database_connection_config(json_payload_entity.payload)

    @staticmethod
    def load_database_datasource_payload(session: Session, _id: str) -> dict:
        json_payload_entity: JsonPayloadEntity = JsonFilesService().get_by_id(session, _id)
        if not json_payload_entity:
            raise ValueError(f"Database datasource '{_id}' not found")
        if json_payload_entity.json_type != JsonType.DATABASE_TABLE.value:
            raise ValueError(f"Datasource '{_id}' is not a database-table datasource")
        return (
            json_payload_entity.payload
            if isinstance(json_payload_entity.payload, dict)
            else {}
        )
