from sqlalchemy.orm import Session

from _alembic.models.scenario_step_entity import ScenarioStepEntity
from elaborations.models.dtos.configuration_step_dtos import DataConfigurationStepDTO
from elaborations.services.steps.step_executor import StepExecutor


class DataStepExecutor(StepExecutor):
    def execute(
        self,
        session: Session,
        scenario_step: ScenarioStepEntity,
        cfg: DataConfigurationStepDTO,
    ) -> list[dict[str, str]]:
        step_code = str(scenario_step.code or scenario_step.id)
        self.log(step_code, f"Try to export {len(cfg.data)} objects")
        return self.execute_operations(
            session,
            scenario_step.id,
            step_code,
            cfg.data,
        )
