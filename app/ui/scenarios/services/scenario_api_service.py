from api_client import api_delete, api_get, api_post, api_put


def get_all_scenarios() -> list[dict]:
    result = api_get("/elaborations/scenario")
    return result if isinstance(result, list) else []


def get_all_steps() -> list[dict]:
    result = api_get("/elaborations/step")
    return result if isinstance(result, list) else []


def get_step_by_id(step_id: str) -> dict:
    return api_get(f"/elaborations/step/{step_id}")


def create_step(payload: dict) -> dict:
    return api_post("/elaborations/step", payload)


def get_all_operations() -> list[dict]:
    result = api_get("/elaborations/operation")
    return result if isinstance(result, list) else []


def create_operation(payload: dict) -> dict:
    return api_post("/elaborations/operation", payload)


def get_scenario_by_id(scenario_id: str) -> dict:
    return api_get(f"/elaborations/scenario/{scenario_id}")


def create_scenario(payload: dict) -> dict:
    return api_post("/elaborations/scenario", payload)


def update_scenario(payload: dict) -> dict:
    return api_put("/elaborations/scenario", payload)


def delete_scenario_by_id(scenario_id: str) -> dict:
    return api_delete(f"/elaborations/scenario/{scenario_id}")


def execute_scenario_by_id(scenario_id: str) -> dict:
    return api_get(f"/elaborations/scenario/{scenario_id}/execute")
