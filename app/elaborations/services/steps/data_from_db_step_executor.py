from sqlalchemy.orm import Session

from _alembic.models.json_payload_entity import JsonPayloadEntity
from _alembic.models.scenario_step_entity import ScenarioStepEntity
from _alembic.models.step_entity import StepEntity
from data_sources.models.database_connection_config_types import DatabaseConnectionConfigTypes
from data_sources.services.alembic.database_connection_service import load_database_connection
from elaborations.models.dtos.configuration_step_dtos import DataFromDbConfigurationStepDto
from elaborations.services.operations.operation_executor_composite import execute_operations
from elaborations.services.steps.step_executor import StepExecutor
from json_utils.models.enums.json_type import JsonType
from json_utils.services.alembic.json_files_service import JsonFilesService
from sqlalchemy_utils.database_table_reader import DatabaseTableReader, ReadTableConfig
from sqlalchemy_utils.engine_factory.sqlalchemy_engine_factory_composite import create_sqlalchemy_engine


class DataFromDbStepExecutor(StepExecutor):

    def execute(self, session: Session, scenario_step: ScenarioStepEntity, step: StepEntity,
                cfg: DataFromDbConfigurationStepDto) -> list[dict[str, str]]:
        connection_id = ""
        table_name = ""
        data_source_id = str(cfg.data_source_id or "").strip()
        if data_source_id:
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
        else:
            # Backward compatibility for existing DATA_FROM_DB steps created before data_source_id.
            configuration_json = (
                step.configuration_json if isinstance(step.configuration_json, dict) else {}
            )
            connection_id = str(configuration_json.get("connection_id") or "").strip()
            table_name = str(configuration_json.get("table_name") or "").strip()
            if not connection_id or not table_name:
                raise ValueError("DATA_FROM_DB step requires data_source_id or legacy connection_id/table_name")

        database_connection_cfg: DatabaseConnectionConfigTypes = load_database_connection(connection_id)
        engine = create_sqlalchemy_engine(database_connection_cfg)

        self.log(scenario_step.step_id, f"Start reading table '{table_name}'")

        operations_id = self.find_all_operations(session, scenario_step.id)

        results: list[dict[str, str]] = []

        rows = DatabaseTableReader.read_full_table(engine, ReadTableConfig(
                table_name=table_name,
        ))
        total_rows = len(rows) if isinstance(rows, list) else 0

        op_result = execute_operations(session, operations_id, rows)

        results.extend(op_result.result)

        self.log(scenario_step.step_id,
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
