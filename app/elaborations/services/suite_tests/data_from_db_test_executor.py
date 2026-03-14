from sqlalchemy.orm import Session

from _alembic.models.json_payload_entity import JsonPayloadEntity
from _alembic.models.suite_test_entity import SuiteTestEntity
from data_sources.models.database_connection_config_types import DatabaseConnectionConfigTypes
from data_sources.services.alembic.database_connection_service import load_database_connection
from elaborations.models.dtos.configuration_test_dtos import DataFromDbConfigurationTestDto
from elaborations.services.suite_tests.test_executor import TestExecutor
from json_utils.models.enums.json_type import JsonType
from json_utils.services.alembic.json_files_service import JsonFilesService
from sqlalchemy_utils.database_table_reader import DatabaseTableReader, ReadTableConfig
from sqlalchemy_utils.engine_factory.sqlalchemy_engine_factory_composite import create_sqlalchemy_engine


class DataFromDbTestExecutor(TestExecutor):

    def execute(
        self,
        session: Session,
        suite_test: SuiteTestEntity,
        cfg: DataFromDbConfigurationTestDto,
    ) -> list[dict[str, str]]:
        test_code = str(suite_test.code or suite_test.id)
        connection_id = ""
        table_name = ""
        data_source_id = str(cfg.dataset_id or "").strip()
        datasource_payload = self.load_database_datasource_payload(session, data_source_id)
        connection_id = str(datasource_payload.get("connection_id") or "").strip()
        object_name = str(datasource_payload.get("object_name") or "").strip()
        schema = str(datasource_payload.get("schema") or "").strip()
        table_name = (
            object_name if not schema or "." in object_name else f"{schema}.{object_name}"
        )
        if not connection_id:
            raise ValueError(f"Database datasource '{data_source_id}' has no connection_id")
        if not table_name:
            raise ValueError(f"Database datasource '{data_source_id}' has no object_name")

        database_connection_cfg: DatabaseConnectionConfigTypes = load_database_connection(connection_id)
        engine = create_sqlalchemy_engine(database_connection_cfg)

        self.log(test_code, f"Start reading table '{table_name}'")

        rows = DatabaseTableReader.read_full_table(engine, ReadTableConfig(
                table_name=table_name,
        ))
        
        total_rows = len(rows) if isinstance(rows, list) else 0

        results = self.execute_operations(
            session,
            suite_test.id,
            test_code,
            rows,
        )

        self.log(test_code,
                 f"Finished reading table '{table_name}'. Total rows processed: {total_rows}")

        return results

    @staticmethod
    def load_database_datasource_payload(session: Session, data_source_id: str) -> dict:
        json_payload_entity: JsonPayloadEntity = JsonFilesService().get_by_id(session, data_source_id)
        if not json_payload_entity:
            raise ValueError(f"Database datasource '{data_source_id}' not found")
        if json_payload_entity.json_type != JsonType.DATABASE_TABLE.value:
            raise ValueError(
                f"Datasource '{data_source_id}' is not a database-table datasource"
            )
        return (
            json_payload_entity.payload
            if isinstance(json_payload_entity.payload, dict)
            else {}
        )
