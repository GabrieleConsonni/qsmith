from pydantic import BaseModel

from elaborations.models.enums.step_type import StepType


class ConfigurationStepDto(BaseModel):
    stepType: str

class SleepConfigurationStepDto(ConfigurationStepDto):
    stepType: str = StepType.SLEEP.value
    duration: int

class DataFromJsonArrayConfigurationStepDto(ConfigurationStepDto):
    stepType: str = StepType.DATA_FROM_JSON_ARRAY.value
    json_array_id: str

class DataConfigurationStepDTO(ConfigurationStepDto):
    stepType: str = StepType.DATA.value
    data: list[dict]

class DataFromDbConfigurationStepDto(ConfigurationStepDto):
    stepType: str = StepType.DATA_FROM_DB.value
    data_source_id: str | None = None

class DataFromQueueConfigurationStepDto(ConfigurationStepDto):
    stepType: str = StepType.DATA_FROM_QUEUE.value
    queue_id: str
    retry: int = 3
    wait_time_seconds: int = 20
    max_messages: int = 1000


ConfigurationStepDtoTypes = SleepConfigurationStepDto | DataConfigurationStepDTO |DataFromJsonArrayConfigurationStepDto | DataFromQueueConfigurationStepDto |DataFromDbConfigurationStepDto


def convert_to_config_step_type(data: dict):
    step_type = data.get("stepType")
    if step_type == StepType.SLEEP.value:
        return SleepConfigurationStepDto(
            duration=data.get("duration")
        )
    elif step_type == StepType.DATA.value:
        return DataConfigurationStepDTO(
            data=data.get("data")
        )
    elif step_type == StepType.DATA_FROM_JSON_ARRAY.value:
        return DataFromJsonArrayConfigurationStepDto(
            json_array_id=data.get("json_array_id")
        )
    elif step_type == StepType.DATA_FROM_DB.value:
        return DataFromDbConfigurationStepDto(
            data_source_id=data.get("data_source_id")
        )
    elif step_type == StepType.DATA_FROM_QUEUE.value:
        return DataFromQueueConfigurationStepDto(
            queue_id=data.get("queue_id"),
            retry=data.get("retry", 3),
            wait_time_seconds=data.get("wait_time_seconds", 20),
            max_messages=data.get("max_messages", 1000)
        )
    else:
        raise ValueError(f"Unsupported step type: {step_type}")
