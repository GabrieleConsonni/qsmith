import time

from sqlalchemy.orm import Session

from _alembic.models.scenario_step_entity import ScenarioStepEntity
from elaborations.models.dtos.configuration_step_dtos import SleepConfigurationStepDto
from elaborations.services.scenarios.run_context import set_context_last
from elaborations.services.steps.step_executor import StepExecutor


class SleepStepExecutor(StepExecutor):
    def execute(
        self,
        session: Session,
        scenario_step: ScenarioStepEntity,
        cfg: SleepConfigurationStepDto,
    ) -> list[dict[str, str]]:
        time.sleep(cfg.duration)
        step_code = str(scenario_step.code or scenario_step.id)
        self.log(step_code, f"Slept for {cfg.duration} seconds")
        output = [{"status": "slept", "duration": str(cfg.duration)}]
        set_context_last(step_code=step_code, data=output)
        return output
