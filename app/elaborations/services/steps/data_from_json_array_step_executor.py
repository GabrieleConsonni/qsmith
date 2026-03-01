from sqlalchemy.orm import Session

from _alembic.models.json_payload_entity import JsonPayloadEntity
from _alembic.models.scenario_step_entity import ScenarioStepEntity
from elaborations.models.dtos.configuration_step_dtos import DataFromJsonArrayConfigurationStepDto
from elaborations.services.steps.step_executor import StepExecutor
from json_utils.services.alembic.json_files_service import JsonFilesService


class DataFromJsonArrayStepExecutor(StepExecutor):
    def execute(
        self,
        session: Session,
        scenario_step: ScenarioStepEntity,
        cfg: DataFromJsonArrayConfigurationStepDto,
    ) -> list[dict[str, str]]:
        json_array = self.load_json_array(session, cfg.json_array_id)

        self.log(
            str(scenario_step.code or scenario_step.id),
            f"Try to elaborate {len(json_array)} objects from JSON array",
        )

        return self.execute_operations(session, scenario_step.id, json_array)

    def load_json_array(self,session:Session, json_array_id:str):
        json_payload_entity: JsonPayloadEntity = JsonFilesService().get_by_id(session, json_array_id)

        if not json_payload_entity:
            raise ValueError(f"Json array '{json_array_id}' not found")

        if isinstance(json_payload_entity.payload, list):
            return json_payload_entity.payload
        else:
            return [json_payload_entity.payload]
