import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from _alembic.models.scenario_execution_entity import ScenarioExecutionEntity
from _alembic.models.scenario_step_entity import ScenarioStepEntity
from _alembic.models.scenario_step_execution_entity import ScenarioStepExecutionEntity
from _alembic.services.session_context_manager import managed_session
from elaborations.models.enums.on_failure import OnFailure
from elaborations.services.alembic.scenario_execution_service import ScenarioExecutionService
from elaborations.services.alembic.scenario_service import ScenarioService
from elaborations.services.alembic.scenario_step_execution_service import (
    ScenarioStepExecutionService,
)
from elaborations.services.alembic.scenario_step_service import ScenarioStepService
from elaborations.services.scenarios.execution_event_bus import (
    publish_execution_event,
    publish_runtime_log_event,
)
from elaborations.services.scenarios.execution_runtime_context import bind_execution_context
from elaborations.services.scenarios.run_context import (
    bind_run_context,
    create_run_context,
    serialize_run_context,
)
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
    scenario_description: str = ""
    event: dict[str, Any] | None = None
    vars_init: dict[str, Any] | None = None
    invocation_id: str | None = None
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
        payload=payload,
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


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _execute(scenario_input: ScenarioExecutionInput):
    with managed_session() as session:
        scenario_execution_service = ScenarioExecutionService()
        scenario_step_execution_service = ScenarioStepExecutionService()

        scenario_steps_all: list[ScenarioStepEntity] = ScenarioStepService().get_all_by_scenario_id(
            session, scenario_input.scenario_id
        )
        target_step_id = str(scenario_input.target_scenario_step_id or "").strip()
        target_step_code = str(
            next(
                (
                    scenario_step.code
                    for scenario_step in scenario_steps_all
                    if str(scenario_step.id) == target_step_id
                ),
                "",
            )
            or ""
        )

        scenario_execution_id = scenario_execution_service.insert(
            session,
            ScenarioExecutionEntity(
                scenario_id=scenario_input.scenario_id,
                scenario_code=scenario_input.scenario_code,
                scenario_description=scenario_input.scenario_description,
                status="running",
                invocation_id=str(scenario_input.invocation_id or "").strip() or None,
                vars_init_json=(
                    scenario_input.vars_init
                    if isinstance(scenario_input.vars_init, dict)
                    else {}
                ),
                include_previous=bool(scenario_input.include_previous),
                requested_step_id=target_step_id or None,
                requested_step_code=target_step_code or None,
            ),
        )
        run_context = create_run_context(
            run_id=scenario_execution_id,
            event=scenario_input.event if isinstance(scenario_input.event, dict) else {},
            initial_vars=(
                scenario_input.vars_init
                if isinstance(scenario_input.vars_init, dict)
                else {}
            ),
            invocation_id=str(scenario_input.invocation_id or "").strip() or None,
        )

        with (
            bind_run_context(run_context),
            bind_execution_context(
                execution_id=scenario_input.execution_id,
                scenario_id=scenario_input.scenario_id,
                scenario_execution_id=scenario_execution_id,
            ),
        ):
            results = []
            total_steps = 0
            completed_steps = 0
            error_count = 0
            first_error_message = ""
            try:
                start_message = f"Starting execution of scenario '{scenario_input.scenario_code}'"
                log(scenario_input.scenario_id, message=start_message)
                publish_execution_event(
                    scenario_input.execution_id,
                    "execution_started",
                    {
                        "scenario_execution_id": scenario_execution_id,
                        "scenario_id": scenario_input.scenario_id,
                        "scenario_code": scenario_input.scenario_code,
                        "target_scenario_step_id": scenario_input.target_scenario_step_id,
                        "include_previous": scenario_input.include_previous,
                    },
                )

                scenario_steps = _resolve_steps_to_execute(
                    scenario_steps_all,
                    scenario_input.target_scenario_step_id,
                    scenario_input.include_previous,
                )

                total_steps = len(scenario_steps)

                publish_execution_event(
                    scenario_input.execution_id,
                    "execution_progress",
                    {
                        "scenario_execution_id": scenario_execution_id,
                        "executed_steps": completed_steps,
                        "total_steps": total_steps,
                    },
                )

                for step_index, scenario_step in enumerate(scenario_steps, start=1):
                    step_execution_id = scenario_step_execution_service.insert(
                        session,
                        ScenarioStepExecutionEntity(
                            scenario_execution_id=scenario_execution_id,
                            scenario_step_id=scenario_step.id,
                            step_code=str(scenario_step.code or ""),
                            step_description=str(scenario_step.description or ""),
                            step_order=scenario_step.order,
                            status="running",
                        ),
                    )

                    step_start_message = (
                        f"Executing scenario_step {scenario_step.order} "
                        f"of {total_steps} in scenario '{scenario_input.scenario_code}'"
                    )
                    log(scenario_input.scenario_id, message=step_start_message)
                    publish_execution_event(
                        scenario_input.execution_id,
                        "step_started",
                        {
                            "scenario_execution_id": scenario_execution_id,
                            "scenario_step_execution_id": step_execution_id,
                            "scenario_step_id": scenario_step.id,
                            "step_code": scenario_step.code,
                            "step_order": int(scenario_step.order),
                            "step_index": step_index,
                            "total_steps": total_steps,
                        },
                    )

                    try:
                        with bind_execution_context(
                            scenario_step_id=scenario_step.id,
                            scenario_step_execution_id=step_execution_id,
                        ):
                            step_results = execute_step(session, scenario_step)
                        results.append(step_results)
                        completed_steps += 1
                        scenario_step_execution_service.update(
                            session,
                            step_execution_id,
                            status="success",
                            error_message=None,
                            finished_at=_utc_now(),
                        )
                        publish_execution_event(
                            scenario_input.execution_id,
                            "step_finished",
                            {
                                "scenario_execution_id": scenario_execution_id,
                                "scenario_step_execution_id": step_execution_id,
                                "scenario_step_id": scenario_step.id,
                                "step_code": scenario_step.code,
                                "step_order": int(scenario_step.order),
                                "status": "success",
                                "result": step_results,
                            },
                        )
                    except Exception as step_exception:
                        error_count += 1
                        if not first_error_message:
                            first_error_message = str(step_exception)
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
                        scenario_step_execution_service.update(
                            session,
                            step_execution_id,
                            status="error",
                            error_message=str(step_exception),
                            finished_at=_utc_now(),
                        )
                        publish_execution_event(
                            scenario_input.execution_id,
                            "step_finished",
                            {
                                "scenario_execution_id": scenario_execution_id,
                                "scenario_step_execution_id": step_execution_id,
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
                                "scenario_execution_id": scenario_execution_id,
                                "executed_steps": completed_steps,
                                "total_steps": total_steps,
                            },
                        )

                finish_message = f"Finished execution of scenario '{scenario_input.scenario_code}'"
                log(
                    scenario_input.scenario_id,
                    message=finish_message,
                    payload={"results": results},
                )
            except Exception as scenario_exception:
                error_count += 1
                if not first_error_message:
                    first_error_message = str(scenario_exception)
                log(
                    scenario_input.scenario_id,
                    message=f"Scenario execution failed for '{scenario_input.scenario_code}'",
                    level=LogLevel.ERROR,
                    payload={"error": str(scenario_exception)},
                )
            finally:
                execution_status = "error" if error_count > 0 else "success"
                scenario_execution_service.update(
                    session,
                    scenario_execution_id,
                    status=execution_status,
                    error_message=(first_error_message or None) if error_count > 0 else None,
                    result_json={
                        "results": results,
                        "artifacts": serialize_run_context(run_context).get("artifacts", {}),
                    },
                    finished_at=_utc_now(),
                )

                payload = {
                    "scenario_execution_id": scenario_execution_id,
                    "scenario_id": scenario_input.scenario_id,
                    "scenario_code": scenario_input.scenario_code,
                    "status": execution_status,
                    "results": results,
                    "errors": error_count,
                    "executed_steps": completed_steps,
                    "total_steps": total_steps,
                }
                if first_error_message:
                    payload["error"] = first_error_message
                publish_execution_event(
                    scenario_input.execution_id,
                    "execution_finished",
                    payload,
                )


class ScenarioExecutorThread(threading.Thread):

    def __init__(
        self,
        scenario_id: str,
        run_event: dict | None = None,
        vars_init: dict | None = None,
        invocation_id: str | None = None,
        target_scenario_step_id: str | None = None,
        include_previous: bool = False,
    ):
        super().__init__(name=f"scenario-{scenario_id}", daemon=True)
        self.execution_id = str(uuid4())
        self.run_event = run_event if isinstance(run_event, dict) else {}
        self.vars_init = vars_init if isinstance(vars_init, dict) else {}
        self.invocation_id = str(invocation_id or "").strip() or None
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
            self.scenario_description = str(scenario.description or "")

    def run(self):
        _execute(
            ScenarioExecutionInput(
                execution_id=self.execution_id,
                scenario_id=self.scenario_id,
                scenario_code=self.scenario_code,
                scenario_description=self.scenario_description,
                event=self.run_event,
                vars_init=self.vars_init,
                invocation_id=self.invocation_id,
                target_scenario_step_id=self.target_scenario_step_id,
                include_previous=self.include_previous,
            )
        )
