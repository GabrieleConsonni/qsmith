from sqlalchemy.orm import Session

from _alembic.models.json_payload_entity import JsonPayloadEntity
from data_sources.models.database_connection_config_types import DatabaseConnectionConfigTypes
from data_sources.models.database_connection_config_types import convert_database_connection_config
from elaborations.models.dtos.configuration_operation_dto import SaveToExternalDBConfigurationOperationDto
from elaborations.services.operations.operation_executor import OperationExecutor, ExecutionResultDto
from elaborations.services.suite_runs.run_context import write_context_path
from json_utils.models.enums.json_type import JsonType
from json_utils.services.alembic.json_files_service import JsonFilesService
from sqlalchemy_utils.database_table_writer import DatabaseTableWriter
from sqlalchemy_utils.engine_factory.sqlalchemy_engine_factory_composite import create_sqlalchemy_engine


class SaveToExternalDbOperationExecutor(OperationExecutor):

    def execute(self, session:Session, operation_id:str, cfg: SaveToExternalDBConfigurationOperationDto, data:list[dict])->ExecutionResultDto:
        connection_id = str(cfg.connection_id or "").strip()
        table_name = str(cfg.table_name or "").strip()

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
        result_payload = {
            "table_name": table_name,
            "inserted_rows": len(data),
            "connection_id": connection_id,
        }
        if cfg.result_target:
            write_context_path(cfg.result_target, result_payload)

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
