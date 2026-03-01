import time

from sqlalchemy.orm import Session

from _alembic.models.scenario_step_entity import ScenarioStepEntity
from elaborations.models.dtos.configuration_step_dtos import SleepConfigurationStepDto
from elaborations.services.steps.step_executor import StepExecutor


class SleepStepExecutor(StepExecutor):
    def execute(
        self,
        session: Session,
        scenario_step: ScenarioStepEntity,
        cfg: SleepConfigurationStepDto,
    ) -> list[dict[str, str]]:
        time.sleep(cfg.duration)
        self.log(str(scenario_step.code or scenario_step.id), f"Slept for {cfg.duration} seconds")
        return [{"status": "slept", "duration": str(cfg.duration)}]
