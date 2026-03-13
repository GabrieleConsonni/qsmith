

from sqlalchemy.orm import Session

from brokers.models.connections.broker_connection_config_types import BrokerConnectionConfigTypes
from brokers.services.alembic.broker_connection_service import load_broker_connection
from brokers.services.alembic.queue_service import QueueService
from brokers.services.connections.queue.queue_connection_service_factory import QueueConnectionServiceFactory
from elaborations.models.dtos.configuration_operation_dto import PublishConfigurationOperationDto
from elaborations.services.operations.operation_executor import OperationExecutor, ExecutionResultDto
from elaborations.services.scenarios.run_context import write_context_path
from json_utils.services.json_service import make_json_safe


class PublishToQueueOperationExecutor(OperationExecutor):
    def execute(self,session:Session,  operation_id:str, cfg: PublishConfigurationOperationDto, data:list[dict])->ExecutionResultDto:
        queue = QueueService().get_by_id(session,cfg.queue_id)
        if not queue:
            raise ValueError(f"Queue '{cfg.queue_id}' not found")
        connection_config: BrokerConnectionConfigTypes = load_broker_connection(queue.broker_id)
        service = QueueConnectionServiceFactory().get_service(connection_config)
        msg = [make_json_safe(item) for item in data]
        service.publish_messages(connection_config, cfg.queue_id, msg)
        message=f"Published {len(data)} message(s) to queue '{queue.code}'"
        result_payload = {
            "queue_id": cfg.queue_id,
            "queue_code": str(queue.code or ""),
            "published": len(data),
        }
        if cfg.result_target:
            write_context_path(cfg.result_target, result_payload)
        self.log(operation_id, message=message)
        return ExecutionResultDto(
            data=data,
            result=[{"message": message}]
        )



