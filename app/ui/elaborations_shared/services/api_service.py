from api_client import api_delete, api_get, api_post
from urllib.parse import quote_plus


def get_all_json_arrays() -> list[dict]:
    result = api_get("/data-source/json-array")
    return result if isinstance(result, list) else []


def get_all_database_datasources() -> list[dict]:
    result = api_get("/data-source/database")
    return result if isinstance(result, list) else []


def get_all_brokers() -> list[dict]:
    result = api_get("/broker/connection")
    return result if isinstance(result, list) else []


def get_queues_by_broker_id(broker_id: str) -> list[dict]:
    broker_id_value = str(broker_id or "").strip()
    if not broker_id_value:
        return []
    result = api_get(f"/broker/{broker_id_value}/queue")
    return result if isinstance(result, list) else []


def get_all_operations() -> list[dict]:
    result = api_get("/elaborations/operation")
    return result if isinstance(result, list) else []


def get_operations_page(page: int, size: int = 5, search: str = "") -> dict:
    page_value = max(int(page or 1), 1)
    size_value = max(int(size or 5), 1)
    search_value = str(search or "").strip()
    search_query = f"&search={quote_plus(search_value)}" if search_value else ""
    result = api_get(
        f"/elaborations/operation?page={page_value}&size={size_value}{search_query}"
    )
    if not isinstance(result, dict):
        return {
            "items": [],
            "page": page_value,
            "size": size_value,
            "total_items": 0,
            "total_pages": 0,
        }
    items = result.get("items")
    return {
        "items": items if isinstance(items, list) else [],
        "page": int(result.get("page") or page_value),
        "size": int(result.get("size") or size_value),
        "total_items": int(result.get("total_items") or 0),
        "total_pages": int(result.get("total_pages") or 0),
    }


def create_operation(payload: dict) -> dict:
    return api_post("/elaborations/operation", payload)


def delete_operation_by_id(operation_id: str) -> dict:
    return api_delete(f"/elaborations/operation/{operation_id}")
