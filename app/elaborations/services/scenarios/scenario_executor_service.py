from elaborations.services.scenarios.scenario_executor_thread import ScenarioExecutorThread


def execute_scenario_by_id(
    scenario_id: str,
    *,
    run_event: dict | None = None,
    vars_init: dict | None = None,
    invocation_id: str | None = None,
):
    executor_thread = ScenarioExecutorThread(
        scenario_id,
        run_event=run_event,
        vars_init=vars_init,
        invocation_id=invocation_id,
    )
    executor_thread.start()
    return executor_thread.execution_id


def execute_scenario_step_by_id(
    scenario_id: str,
    scenario_step_id: str,
    include_previous: bool = False,
):
    executor_thread = ScenarioExecutorThread(
        scenario_id=scenario_id,
        target_scenario_step_id=scenario_step_id,
        include_previous=include_previous,
    )
    executor_thread.start()
    return executor_thread.execution_id
