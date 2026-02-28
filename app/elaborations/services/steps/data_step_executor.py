from sqlalchemy.orm import Session

from _alembic.models.scenario_step_entity import ScenarioStepEntity
from _alembic.models.step_entity import StepEntity
from elaborations.models.dtos.configuration_step_dtos import DataConfigurationStepDTO
from elaborations.services.steps.step_executor import StepExecutor


class DataStepExecutor(StepExecutor):
    def execute(self, session:Session, scenario_step:ScenarioStepEntity, step:StepEntity, cfg: DataConfigurationStepDTO) -> list[dict[str, str]]:
        self.log(scenario_step.step_id, f"Try to export {len(cfg.data)} objects")
        return self.execute_operations(session, scenario_step.id, cfg.data)
