from elaborations.services.scenarios.scenario_executor_thread import ScenarioExecutorThread

def execute_scenario_by_id(scenario_id: str):
    executor_thread = ScenarioExecutorThread(scenario_id)
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
