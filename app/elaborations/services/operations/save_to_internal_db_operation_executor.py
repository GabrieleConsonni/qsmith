import json
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from _alembic.services.alembic_config_service import url_from_env
from elaborations.models.dtos.configuration_operation_dto import SaveInternalDBConfigurationOperationDto
from elaborations.services.operations.operation_executor import OperationExecutor, ExecutionResultDto
from sqlalchemy_utils.database_table_writer import DatabaseTableWriter


class SaveInternalDbOperationExecutor(OperationExecutor):
    def execute(self, session:Session,  operation_id:str, cfg: SaveInternalDBConfigurationOperationDto, data:list[dict])->ExecutionResultDto:
        engine = create_engine(url_from_env())

        if not data or len(data) == 0:
            message = f"No data to insert into {cfg.table_name} table"
            self.log(operation_id, message)
            return ExecutionResultDto(
                data=data,
                result=[{"message": message}]
            )

        sample_row = {}
        for d in data:
            for key, value in d.items():
                sample_row[key] = value

        table = DatabaseTableWriter.ensure_table_exists(engine, cfg.table_name, sample_row)
        DatabaseTableWriter.insert_rows(engine, table, data)

        message = f"Created {len(data)} rows in {cfg.table_name} table"

        self.log(operation_id, message)

        return ExecutionResultDto(
            data=data,
            result=[{"message": message}]
        )
