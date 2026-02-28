import time

from sqlalchemy.orm import Session

from _alembic.models.scenario_step_entity import ScenarioStepEntity
from _alembic.models.step_entity import StepEntity
from brokers.models.connections.broker_connection_config_types import BrokerConnectionConfigTypes
from brokers.services.alembic.broker_connection_service import load_broker_connection
from brokers.services.alembic.queue_service import QueueService
from brokers.services.connections.queue.queue_connection_service_factory import QueueConnectionServiceFactory
from elaborations.models.dtos.configuration_step_dtos import DataFromQueueConfigurationStepDto
from elaborations.services.steps.step_executor import StepExecutor


class DataFromQueueStepExecutor(StepExecutor):

    def execute(self, session:Session, scenario_step:ScenarioStepEntity, step:StepEntity, cfg: DataFromQueueConfigurationStepDto) -> list[dict[str, str]]:
        queue = QueueService().get_by_id(session, cfg.queue_id)
        if not queue:
            raise ValueError(f"Queue '{cfg.queue_id}' not found")
        broker_connection:BrokerConnectionConfigTypes = load_broker_connection(queue.broker_id)

        service = QueueConnectionServiceFactory.get_service(broker_connection)

        retry = cfg.retry
        wait_time_seconds = cfg.wait_time_seconds
        max_messages = cfg.max_messages

        all_msgs = []

        while self.work_is_not_finished(all_msgs, max_messages, retry):
            remaining_messages = max_messages - len(all_msgs)
            if remaining_messages <= 0:
                break

            msgs = service.receive_messages(
                broker_connection,
                queue_id=cfg.queue_id,
                max_messages=remaining_messages,
            )

            if len(msgs) == 0:
                time.sleep(wait_time_seconds)
                retry -= 1
                continue

            all_msgs.extend(msgs)

        self.log(scenario_step.step_id, f"Try to export {len(all_msgs)} messages read from queue '{queue.code}'")

        return self.execute_operations(session, scenario_step.id, all_msgs)

    @staticmethod
    def work_is_not_finished(all_msgs, max_messages, retry):
        right_size = len(all_msgs) < max_messages
        return  retry > 0 and right_size
