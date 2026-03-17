import json
import time

from sqlalchemy.orm import Session

from brokers.models.connections.broker_connection_config_types import BrokerConnectionConfigTypes
from brokers.services.alembic.broker_connection_service import load_broker_connection
from brokers.services.alembic.queue_service import QueueService
from brokers.services.connections.queue.queue_connection_service_factory import (
    QueueConnectionServiceFactory,
)
from data_sources.services.dataset_query_service import DatasetQueryService
from elaborations.models.dtos.configuration_command_dto import (
    ConstantSourceType,
    InitConstantConfigurationCommandDto,
)
from elaborations.services.operations.command_executor import (
    ExecutionResultDto,
    OperationExecutor,
)
from elaborations.services.suite_runs.run_context import write_context_path
from json_utils.services.alembic.json_files_service import JsonFilesService


class DataOperationExecutor(OperationExecutor):
    def execute(
        self,
        session: Session,
        operation_id: str,
        cfg: InitConstantConfigurationCommandDto,
        data,
    ) -> ExecutionResultDto:
        resolved_value = self._load_value(session, cfg, data)
        target_path = f"$.{cfg.context}.constants.{cfg.name}"
        write_context_path(target_path, resolved_value)
        message = f"Initialized constant '{cfg.name}' in context '{cfg.context}'."
        self.log(
            operation_id,
            message=message,
            payload={
                "name": cfg.name,
                "context": cfg.context,
                "source_type": cfg.sourceType,
            },
        )
        return ExecutionResultDto(
            data=resolved_value,
            result=[
                {
                    "message": message,
                    "name": cfg.name,
                    "context": cfg.context,
                    "sourceType": cfg.sourceType,
                }
            ],
        )

    def _load_value(self, session: Session, cfg: InitConstantConfigurationCommandDto, data):
        if cfg.sourceType == ConstantSourceType.RAW.value:
            return cfg.value
        if cfg.sourceType == ConstantSourceType.JSON.value:
            return cfg.value
        if cfg.sourceType == ConstantSourceType.JSON_ARRAY.value:
            return self._load_json_array(session, cfg.json_array_id)
        if cfg.sourceType == ConstantSourceType.DATASET.value:
            return self._load_dataset(session, cfg.dataset_id)
        if cfg.sourceType == ConstantSourceType.SQS_QUEUE.value:
            return self._load_queue_messages(session, cfg)
        return data

    @staticmethod
    def _load_json_array(session: Session, json_array_id: str | None):
        json_payload_entity = JsonFilesService().get_by_id(
            session,
            str(json_array_id or "").strip(),
        )
        if not json_payload_entity:
            raise ValueError(f"Json array '{json_array_id}' not found")
        payload = json_payload_entity.payload
        return payload if isinstance(payload, list) else [payload]

    @staticmethod
    def _load_dataset(session: Session, data_source_id: str | None):
        dataset = DatasetQueryService.get_dataset_or_raise_for_runtime(
            session,
            str(data_source_id or "").strip(),
        )
        return DatasetQueryService.load_rows_for_runtime(dataset)

    @staticmethod
    def _load_queue_messages(session: Session, cfg: InitConstantConfigurationCommandDto):
        queue = QueueService().get_by_id(session, cfg.queue_id)
        if not queue:
            raise ValueError(f"Queue '{cfg.queue_id}' not found")
        broker_connection: BrokerConnectionConfigTypes = load_broker_connection(queue.broker_id)
        service = QueueConnectionServiceFactory.get_service(broker_connection)

        retry = cfg.retry
        all_msgs = []
        while retry > 0 and len(all_msgs) < cfg.max_messages:
            remaining_messages = cfg.max_messages - len(all_msgs)
            msgs = service.receive_messages(
                broker_connection,
                queue_id=cfg.queue_id,
                max_messages=remaining_messages,
            )
            if not msgs:
                time.sleep(cfg.wait_time_seconds)
                retry -= 1
                continue
            all_msgs.extend(msgs)

        payload_rows = []
        for index, message in enumerate(all_msgs):
            if not isinstance(message, dict):
                raise ValueError(f"Message {index + 1} is not valid JSON.")
            body_value = message.get("Body") if "Body" in message else message
            if isinstance(body_value, str):
                try:
                    body_value = json.loads(body_value)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid body in message {index + 1}: {str(exc)}") from exc
            payload_rows.append(body_value)
        return payload_rows

