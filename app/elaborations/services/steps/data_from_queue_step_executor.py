import json
import time

from sqlalchemy.orm import Session

from _alembic.models.scenario_step_entity import ScenarioStepEntity
from brokers.models.connections.broker_connection_config_types import BrokerConnectionConfigTypes
from brokers.services.alembic.broker_connection_service import load_broker_connection
from brokers.services.alembic.queue_service import QueueService
from brokers.services.connections.queue.queue_connection_service_factory import QueueConnectionServiceFactory
from elaborations.models.dtos.configuration_step_dtos import DataFromQueueConfigurationStepDto
from elaborations.services.steps.step_executor import StepExecutor
from logs.models.enums.log_level import LogLevel


class DataFromQueueStepExecutor(StepExecutor):

    def execute(
        self,
        session: Session,
        scenario_step: ScenarioStepEntity,
        cfg: DataFromQueueConfigurationStepDto,
    ) -> list[dict[str, str]]:
        step_code = str(scenario_step.code or scenario_step.id)
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

        self.log(
            step_code,
            f"Try to export {len(all_msgs)} messages read from queue '{queue.code}'",
        )

        extracted_payload, error = self._extract_json_array_from_messages(all_msgs)

        return (
            self.execute_operations(
                session,
                scenario_step.id,
                step_code,
                extracted_payload,
            )
            if not error
            else self._handle_error(scenario_step, error)
        )
    
    def _extract_json_array_from_messages(self, messages: list[object]) -> tuple[list[object] | None, str | None]:
        extracted: list[object] = []
        for index, message in enumerate(messages):
            if not isinstance(message, dict):
                return None, f"Messaggio {index + 1} non valido."

            # Accept both SQS-shaped messages (with Body) and already-decoded payloads.
            body_value = message.get("Body") if "Body" in message else message
            if isinstance(body_value, str):
                try:
                    body_value = json.loads(body_value)
                except json.JSONDecodeError as exc:
                    return None, f"Body non valido nel messaggio {index + 1}: {str(exc)}"
            extracted.append(body_value)
        return extracted, None
    
    def _handle_error(self, scenario_step: ScenarioStepEntity, error_message: str) -> list[dict[str, str]]:
        self.log(
            str(scenario_step.code or scenario_step.id),
            f"Error extracting messages: {error_message}",
            level=LogLevel.ERROR,
        )
        return [{"error": error_message}]

    @staticmethod
    def work_is_not_finished(all_msgs, max_messages, retry):
        right_size = len(all_msgs) < max_messages
        return  retry > 0 and right_size
