import threading
from dataclasses import dataclass
from uuid import uuid4

from _alembic.models.scenario_step_entity import ScenarioStepEntity
from _alembic.services.session_context_manager import managed_session
from elaborations.models.enums.on_failure import OnFailure
from elaborations.services.alembic.scenario_service import ScenarioService
from elaborations.services.alembic.scenario_step_service import ScenarioStepService
from elaborations.services.scenarios.execution_event_bus import (
    publish_execution_event,
    publish_runtime_log_event,
)
from elaborations.services.scenarios.execution_runtime_context import bind_execution_context
from elaborations.services.steps.step_executor_composite import execute_step
from exceptions.app_exception import QsmithAppException
from logs.models.dtos.log_dto import LogDto
from logs.models.enums.log_level import LogLevel
from logs.models.enums.log_subject_type import LogSubjectType
from logs.services.alembic.log_service import LogService


@dataclass
class ScenarioExecutionInput:
    execution_id: str
    scenario_id: str
    scenario_code: str
    target_scenario_step_id: str | None = None
    include_previous: bool = False


def log(
    scenario_id: str,
    message: str,
    level: LogLevel = LogLevel.INFO,
    payload: dict | list[dict] = None,
):
    log_dto = LogDto(
        subject_type=LogSubjectType.SCENARIO_EXECUTION,
        subject=scenario_id,
        message=message,
        level=level,
        payload=payload
    )
    LogService().log(log_dto)
    publish_runtime_log_event(
        subject_type=LogSubjectType.SCENARIO_EXECUTION,
        subject=scenario_id,
        level=level,
        message=message,
        payload=payload,
    )


def _resolve_steps_to_execute(
    scenario_steps: list[ScenarioStepEntity],
    target_scenario_step_id: str | None,
    include_previous: bool,
) -> list[ScenarioStepEntity]:
    if not target_scenario_step_id:
        return scenario_steps

    target_index = next(
        (
            idx
            for idx, scenario_step in enumerate(scenario_steps)
            if str(scenario_step.id) == str(target_scenario_step_id)
        ),
        -1,
    )
    if target_index < 0:
        raise QsmithAppException(
            f"Scenario step with id '{target_scenario_step_id}' not found in scenario"
        )
    if include_previous:
        return scenario_steps[: target_index + 1]
    return [scenario_steps[target_index]]


def _execute(scenario_input: ScenarioExecutionInput):
    with managed_session() as session:
        with bind_execution_context(
            execution_id=scenario_input.execution_id,
            scenario_id=scenario_input.scenario_id,
        ):
            results = []
            total_steps = 0
            completed_steps = 0
            error_count = 0
            try:
                start_message = f"Starting execution of scenario '{scenario_input.scenario_code}'"
                log(scenario_input.scenario_id, message=start_message)
                publish_execution_event(
                    scenario_input.execution_id,
                    "execution_started",
                    {
                        "scenario_id": scenario_input.scenario_id,
                        "scenario_code": scenario_input.scenario_code,
                        "target_scenario_step_id": scenario_input.target_scenario_step_id,
                        "include_previous": scenario_input.include_previous,
                    },
                )

                scenario_steps: list[ScenarioStepEntity] = ScenarioStepService().get_all_by_scenario_id(
                    session, scenario_input.scenario_id
                )
                scenario_steps = _resolve_steps_to_execute(
                    scenario_steps,
                    scenario_input.target_scenario_step_id,
                    scenario_input.include_previous,
                )

                total_steps = len(scenario_steps)

                publish_execution_event(
                    scenario_input.execution_id,
                    "execution_progress",
                    {
                        "executed_steps": completed_steps,
                        "total_steps": total_steps,
                    },
                )

                for step_index, scenario_step in enumerate(scenario_steps, start=1):
                    step_start_message = (
                        f"Executing scenario_step {scenario_step.order} "
                        f"of {total_steps} in scenario '{scenario_input.scenario_code}'"
                    )
                    log(scenario_input.scenario_id, message=step_start_message)
                    publish_execution_event(
                        scenario_input.execution_id,
                        "step_started",
                        {
                            "scenario_step_id": scenario_step.id,
                            "step_code": scenario_step.code,
                            "step_order": int(scenario_step.order),
                            "step_index": step_index,
                            "total_steps": total_steps,
                        },
                    )

                    try:
                        with bind_execution_context(scenario_step_id=scenario_step.id):
                            step_results = execute_step(session, scenario_step)
                        results.append(step_results)
                        completed_steps += 1
                        publish_execution_event(
                            scenario_input.execution_id,
                            "step_finished",
                            {
                                "scenario_step_id": scenario_step.id,
                                "step_code": scenario_step.code,
                                "step_order": int(scenario_step.order),
                                "status": "success",
                                "result": step_results,
                            },
                        )
                    except Exception as step_exception:
                        error_count += 1
                        error_message = (
                            f"Error executing scenario_step n.'{scenario_step.order}' "
                            f"in scenario '{scenario_input.scenario_code}'"
                        )
                        log(
                            scenario_input.scenario_id,
                            message=error_message,
                            level=LogLevel.ERROR,
                            payload={"error": str(step_exception)},
                        )
                        publish_execution_event(
                            scenario_input.execution_id,
                            "step_finished",
                            {
                                "scenario_step_id": scenario_step.id,
                                "step_code": scenario_step.code,
                                "step_order": int(scenario_step.order),
                                "status": "error",
                                "error": str(step_exception),
                            },
                        )
                        if scenario_step.on_failure == OnFailure.ABORT:
                            break
                    finally:
                        publish_execution_event(
                            scenario_input.execution_id,
                            "execution_progress",
                            {
                                "executed_steps": completed_steps,
                                "total_steps": total_steps,
                            },
                        )

                finish_message = f"Finished execution of scenario '{scenario_input.scenario_code}'"
                log(scenario_input.scenario_id, message=finish_message, payload={"results": results})
            except Exception as scenario_exception:
                error_count += 1
                log(
                    scenario_input.scenario_id,
                    message=f"Scenario execution failed for '{scenario_input.scenario_code}'",
                    level=LogLevel.ERROR,
                    payload={"error": str(scenario_exception)},
                )
            finally:
                execution_status = "error" if error_count > 0 else "success"
                publish_execution_event(
                    scenario_input.execution_id,
                    "execution_finished",
                    {
                        "scenario_id": scenario_input.scenario_id,
                        "scenario_code": scenario_input.scenario_code,
                        "status": execution_status,
                        "results": results,
                        "errors": error_count,
                        "executed_steps": completed_steps,
                        "total_steps": total_steps,
                    },
                )


class ScenarioExecutorThread(threading.Thread):

    def __init__(
        self,
        scenario_id: str,
        target_scenario_step_id: str | None = None,
        include_previous: bool = False,
    ):
        super().__init__(name=f"scenario-{scenario_id}", daemon=True)
        self.execution_id = str(uuid4())
        self.target_scenario_step_id = target_scenario_step_id
        self.include_previous = include_previous
        with managed_session() as session:
            scenario = ScenarioService().get_by_id(session, scenario_id)
            if not scenario:
                message = f"Scenario with id '{scenario_id}' not found"
                log(scenario_id, message=message, level=LogLevel.ERROR)
                raise QsmithAppException(message)
            self.scenario_id = scenario.id
            self.scenario_code = scenario.code

    def run(self):
        _execute(ScenarioExecutionInput(
            execution_id=self.execution_id,
            scenario_id=self.scenario_id,
            scenario_code=self.scenario_code,
            target_scenario_step_id=self.target_scenario_step_id,
            include_previous=self.include_previous,
        ))
