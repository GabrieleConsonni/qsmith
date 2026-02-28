import time

from sqlalchemy.orm import Session

from _alembic.models.scenario_step_entity import ScenarioStepEntity
from _alembic.models.step_entity import StepEntity
from elaborations.models.dtos.configuration_step_dtos import SleepConfigurationStepDto
from elaborations.services.steps.step_executor import StepExecutor


class SleepStepExecutor(StepExecutor):
    def execute(self, session:Session, scenario_step:ScenarioStepEntity, step:StepEntity, cfg: SleepConfigurationStepDto) -> list[dict[str, str]]:
        time.sleep(cfg.duration)
        self.log(scenario_step.step_id, f"Slept for {cfg.duration} seconds")
        return [{"status": "slept", "duration": str(cfg.duration)}]
