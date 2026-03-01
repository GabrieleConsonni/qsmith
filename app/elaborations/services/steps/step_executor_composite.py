from sqlalchemy.orm import Session

from _alembic.models.scenario_step_entity import ScenarioStepEntity
from elaborations.models.dtos.configuration_step_dtos import (
    ConfigurationStepDto,
    ConfigurationStepDtoTypes,
    DataConfigurationStepDTO,
    DataFromDbConfigurationStepDto,
    DataFromJsonArrayConfigurationStepDto,
    DataFromQueueConfigurationStepDto,
    SleepConfigurationStepDto,
    convert_to_config_step_type,
)
from elaborations.services.steps.data_from_db_step_executor import DataFromDbStepExecutor
from elaborations.services.steps.data_from_json_array_step_executor import DataFromJsonArrayStepExecutor
from elaborations.services.steps.data_from_queue_step_executor import DataFromQueueStepExecutor
from elaborations.services.steps.data_step_executor import DataStepExecutor
from elaborations.services.steps.sleep_step_executor import SleepStepExecutor
from elaborations.services.steps.step_executor import StepExecutor

_EXECUTOR_MAPPING: dict[type[ConfigurationStepDto], type[StepExecutor]] = {
    SleepConfigurationStepDto: SleepStepExecutor,
    DataConfigurationStepDTO: DataStepExecutor,
    DataFromJsonArrayConfigurationStepDto: DataFromJsonArrayStepExecutor,
    DataFromDbConfigurationStepDto: DataFromDbStepExecutor,
    DataFromQueueConfigurationStepDto: DataFromQueueStepExecutor,
}


def execute_step(session: Session, scenario_step: ScenarioStepEntity) -> list[dict[str, str]]:
    scenario_cfg = (
        scenario_step.configuration_json
        if isinstance(scenario_step.configuration_json, dict)
        else {}
    )
    cfg: ConfigurationStepDtoTypes = convert_to_config_step_type(scenario_cfg)

    clazz = _EXECUTOR_MAPPING.get(type(cfg))
    if clazz is None:
        supported_types = list(_EXECUTOR_MAPPING.keys())
        raise ValueError(
            f"Unsupported step type: {cfg}. "
            f"Supported types: {supported_types}"
        )
    step_executor = clazz()
    return step_executor.execute(session, scenario_step, cfg)
