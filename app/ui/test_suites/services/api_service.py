from urllib.parse import quote_plus

from api_client import api_delete, api_get, api_post, api_put


def get_all_test_suites() -> list[dict]:
    result = api_get("/elaborations/test-suite")
    return result if isinstance(result, list) else []


def get_test_suite_by_id(test_suite_id: str) -> dict:
    return api_get(f"/elaborations/test-suite/{test_suite_id}")


def create_test_suite(payload: dict) -> dict:
    return api_post("/elaborations/test-suite", payload)


def update_test_suite(payload: dict) -> dict:
    return api_put("/elaborations/test-suite", payload)


def delete_test_suite_by_id(test_suite_id: str) -> dict:
    return api_delete(f"/elaborations/test-suite/{test_suite_id}")


def execute_test_suite_by_id(test_suite_id: str) -> dict:
    return api_get(f"/elaborations/test-suite/{test_suite_id}/execute")


def execute_test_by_id(test_suite_id: str, suite_item_id: str) -> dict:
    return api_post(
        f"/elaborations/test-suite/{test_suite_id}/test/{suite_item_id}/execute",
        {},
    )


def get_test_suite_executions(
    test_suite_id: str | None = None,
    limit: int = 50,
) -> list[dict]:
    limit_value = max(int(limit or 50), 1)
    suite_id = str(test_suite_id or "").strip()
    query_parts = [f"limit={limit_value}"]
    if suite_id:
        query_parts.append(f"test_suite_id={quote_plus(suite_id)}")
    result = api_get(f"/elaborations/test-suite-execution?{'&'.join(query_parts)}")
    return result if isinstance(result, list) else []


def delete_test_suite_execution_by_id(execution_id: str) -> dict:
    return api_delete(f"/elaborations/test-suite-execution/{execution_id}")
