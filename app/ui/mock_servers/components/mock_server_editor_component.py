import json
from uuid import uuid4

import streamlit as st

from mock_servers.services.data_loader_service import MOCK_SERVERS_KEY, load_mock_servers
from mock_servers.services.mock_server_api_service import (
    activate_mock_server,
    deactivate_mock_server,
    get_mock_server_by_id,
    update_mock_server,
)
from mock_servers.services.state_keys import (
    MOCK_SERVER_EDITOR_DRAFT_KEY,
    MOCK_SERVER_EDITOR_FEEDBACK_KEY,
    MOCK_SERVER_EDITOR_NONCE_KEY,
    SELECTED_MOCK_SERVER_ID_KEY,
)
from scenarios.components.scenario_operation_component import (
    render_add_step_operation_dialog,
    render_operation_component,
)
from scenarios.services.data_loader_service import (
    load_operations_catalog,
    load_step_editor_brokers,
    load_step_editor_queues_for_broker,
)
from scenarios.services.state_keys import (
    ADD_STEP_OPERATION_DIALOG_NONCE_KEY,
    ADD_STEP_OPERATION_DIALOG_OPEN_KEY,
    ADD_STEP_OPERATION_DIALOG_TARGET_STEP_UI_KEY,
    OPERATIONS_CATALOG_KEY,
    STEP_EDITOR_BROKERS_KEY,
)

MOCK_SERVERS_PAGE_PATH = "pages/MockServers.py"
HTTP_METHOD_OPTIONS = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]


def _new_ui_key() -> str:
    return uuid4().hex[:10]


def _safe_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return default
        try:
            return int(float(stripped))
        except ValueError:
            return default
    return default


def _normalize_endpoint(raw_value: object) -> str:
    return str(raw_value or "").strip().strip("/")


def _normalize_path(raw_value: object) -> str:
    path = str(raw_value or "").strip()
    if not path:
        return "/"
    if not path.startswith("/"):
        path = f"/{path}"
    if len(path) > 1:
        path = path.rstrip("/")
    return path


def _pretty_json(value: object) -> str:
    return json.dumps(value, indent=2, ensure_ascii=True)


def _parse_json_dict(
    raw_value: str,
    *,
    field_label: str,
    allow_empty: bool = True,
) -> tuple[dict | None, str | None]:
    raw_text = str(raw_value or "").strip()
    if not raw_text:
        if allow_empty:
            return {}, None
        return None, f"{field_label}: valore obbligatorio."
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        return None, f"{field_label}: JSON non valido ({str(exc)})."
    if not isinstance(parsed, dict):
        return None, f"{field_label}: deve essere un oggetto JSON."
    return parsed, None


def _parse_json_body(raw_value: str) -> object:
    raw_text = str(raw_value or "").strip()
    if not raw_text:
        return None
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return raw_text


def _operation_payload(operation: dict) -> dict:
    cfg = operation.get("configuration_json") if isinstance(operation.get("configuration_json"), dict) else {}
    return {
        "order": _safe_int(operation.get("order"), 0),
        "code": str(operation.get("code") or "").strip(),
        "description": str(operation.get("description") or ""),
        "cfg": cfg,
    }


def _api_payload(api_entry: dict) -> dict:
    cfg = api_entry.get("configuration_json") if isinstance(api_entry.get("configuration_json"), dict) else {}
    method = str(cfg.get("method") or api_entry.get("method") or "GET").strip().upper()
    if method not in HTTP_METHOD_OPTIONS:
        method = "GET"
    cfg = {**cfg, "method": method, "path": _normalize_path(cfg.get("path") or api_entry.get("path"))}
    return {
        "order": _safe_int(api_entry.get("order"), 0),
        "code": str(api_entry.get("code") or "").strip(),
        "description": str(api_entry.get("description") or ""),
        "cfg": cfg,
        "operations": [
            _operation_payload(item)
            for item in (api_entry.get("operations") or [])
            if isinstance(item, dict)
        ],
    }


def _queue_payload(queue_entry: dict) -> dict:
    cfg = queue_entry.get("configuration_json") if isinstance(queue_entry.get("configuration_json"), dict) else {}
    return {
        "order": _safe_int(queue_entry.get("order"), 0),
        "code": str(queue_entry.get("code") or "").strip(),
        "description": str(queue_entry.get("description") or ""),
        "queue_id": str(queue_entry.get("queue_id") or "").strip(),
        "cfg": cfg,
        "operations": [
            _operation_payload(item)
            for item in (queue_entry.get("operations") or [])
            if isinstance(item, dict)
        ],
    }


def _validate_draft(draft: dict) -> str | None:
    if not str(draft.get("id") or "").strip():
        return "Mock server non valido."
    if not str(draft.get("code") or "").strip():
        return "Il campo Code e' obbligatorio."
    if not _normalize_endpoint(draft.get("endpoint")):
        return "Il campo Endpoint e' obbligatorio."

    for idx, api_entry in enumerate(draft.get("apis") or []):
        if not str(api_entry.get("code") or "").strip():
            return f"API #{idx + 1}: code obbligatorio."
        cfg = api_entry.get("configuration_json") if isinstance(api_entry.get("configuration_json"), dict) else {}
        method = str(cfg.get("method") or "").strip().upper()
        if method not in HTTP_METHOD_OPTIONS:
            return f"API #{idx + 1}: method non valido."
        if not _normalize_path(cfg.get("path")):
            return f"API #{idx + 1}: path obbligatorio."
        for op_idx, operation in enumerate(api_entry.get("operations") or []):
            if not str(operation.get("code") or "").strip():
                return f"API #{idx + 1}, operation #{op_idx + 1}: code obbligatorio."
            operation_cfg = (
                operation.get("configuration_json")
                if isinstance(operation.get("configuration_json"), dict)
                else {}
            )
            if not str(operation_cfg.get("operationType") or "").strip():
                return f"API #{idx + 1}, operation #{op_idx + 1}: operationType obbligatorio."

    for idx, queue_entry in enumerate(draft.get("queues") or []):
        if not str(queue_entry.get("code") or "").strip():
            return f"Queue #{idx + 1}: code obbligatorio."
        if not str(queue_entry.get("queue_id") or "").strip():
            return f"Queue #{idx + 1}: queue obbligatoria."
        for op_idx, operation in enumerate(queue_entry.get("operations") or []):
            if not str(operation.get("code") or "").strip():
                return f"Queue #{idx + 1}, operation #{op_idx + 1}: code obbligatorio."
            operation_cfg = (
                operation.get("configuration_json")
                if isinstance(operation.get("configuration_json"), dict)
                else {}
            )
            if not str(operation_cfg.get("operationType") or "").strip():
                return f"Queue #{idx + 1}, operation #{op_idx + 1}: operationType obbligatorio."
    return None


def _server_payload(draft: dict) -> dict:
    return {
        "id": str(draft.get("id") or "").strip(),
        "code": str(draft.get("code") or "").strip(),
        "description": str(draft.get("description") or ""),
        "cfg": {"endpoint": _normalize_endpoint(draft.get("endpoint"))},
        "apis": [
            _api_payload(api_entry)
            for api_entry in (draft.get("apis") or [])
            if isinstance(api_entry, dict)
        ],
        "queues": [
            _queue_payload(queue_entry)
            for queue_entry in (draft.get("queues") or [])
            if isinstance(queue_entry, dict)
        ],
        "is_active": bool(draft.get("is_active")),
    }


def _operation_from_api_payload(operation: dict, op_idx: int) -> dict:
    cfg = operation.get("configuration_json") if isinstance(operation.get("configuration_json"), dict) else {}
    return {
        "id": operation.get("id"),
        "order": _safe_int(operation.get("order"), op_idx + 1),
        "code": str(operation.get("code") or ""),
        "description": str(operation.get("description") or ""),
        "operation_type": str(operation.get("operation_type") or cfg.get("operationType") or ""),
        "configuration_json": cfg,
        "_ui_key": _new_ui_key(),
    }


def _api_from_server_payload(api_entry: dict, api_idx: int) -> dict:
    cfg = api_entry.get("configuration_json") if isinstance(api_entry.get("configuration_json"), dict) else {}
    method = str(cfg.get("method") or api_entry.get("method") or "GET").strip().upper()
    path = _normalize_path(cfg.get("path") or api_entry.get("path"))
    cfg = {**cfg, "method": method, "path": path}
    operations = [
        _operation_from_api_payload(operation, op_idx)
        for op_idx, operation in enumerate(api_entry.get("operations") or [])
        if isinstance(operation, dict)
    ]
    return {
        "id": api_entry.get("id"),
        "order": _safe_int(api_entry.get("order"), api_idx + 1),
        "code": str(api_entry.get("code") or ""),
        "description": str(api_entry.get("description") or ""),
        "method": method,
        "path": path,
        "configuration_json": cfg,
        "operations": operations,
        "_ui_key": _new_ui_key(),
    }


def _queue_from_server_payload(queue_entry: dict, queue_idx: int) -> dict:
    cfg = queue_entry.get("configuration_json") if isinstance(queue_entry.get("configuration_json"), dict) else {}
    operations = [
        _operation_from_api_payload(operation, op_idx)
        for op_idx, operation in enumerate(queue_entry.get("operations") or [])
        if isinstance(operation, dict)
    ]
    return {
        "id": queue_entry.get("id"),
        "order": _safe_int(queue_entry.get("order"), queue_idx + 1),
        "code": str(queue_entry.get("code") or ""),
        "description": str(queue_entry.get("description") or ""),
        "queue_id": str(queue_entry.get("queue_id") or ""),
        "configuration_json": cfg,
        "operations": operations,
        "_ui_key": _new_ui_key(),
    }


def _build_server_draft(server_item: dict) -> dict:
    apis = [
        _api_from_server_payload(api_entry, api_idx)
        for api_idx, api_entry in enumerate(server_item.get("apis") or [])
        if isinstance(api_entry, dict)
    ]
    queues = [
        _queue_from_server_payload(queue_entry, queue_idx)
        for queue_idx, queue_entry in enumerate(server_item.get("queues") or [])
        if isinstance(queue_entry, dict)
    ]
    apis.sort(key=lambda item: _safe_int(item.get("order"), 0))
    queues.sort(key=lambda item: _safe_int(item.get("order"), 0))
    return {
        "id": str(server_item.get("id") or ""),
        "code": str(server_item.get("code") or ""),
        "description": str(server_item.get("description") or ""),
        "endpoint": _normalize_endpoint(server_item.get("endpoint")),
        "is_active": bool(server_item.get("is_active")),
        "apis": apis,
        "queues": queues,
    }


def _find_server_by_id(mock_server_id: str) -> dict | None:
    server_id = str(mock_server_id or "").strip()
    if not server_id:
        return None
    servers = st.session_state.get(MOCK_SERVERS_KEY, [])
    if isinstance(servers, list):
        for server in servers:
            if not isinstance(server, dict):
                continue
            if str(server.get("id") or "").strip() == server_id:
                return server
    try:
        payload = get_mock_server_by_id(server_id)
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _resolve_selected_server_id() -> str:
    selected_id = str(st.session_state.get(SELECTED_MOCK_SERVER_ID_KEY) or "").strip()
    if selected_id:
        return selected_id

    servers = st.session_state.get(MOCK_SERVERS_KEY, [])
    if not isinstance(servers, list):
        return ""
    for server in servers:
        if not isinstance(server, dict):
            continue
        server_id = str(server.get("id") or "").strip()
        if server_id:
            st.session_state[SELECTED_MOCK_SERVER_ID_KEY] = server_id
            return server_id
    return ""


def _ensure_editor_draft():
    load_mock_servers(force=False)
    selected_id = _resolve_selected_server_id()
    current_draft = st.session_state.get(MOCK_SERVER_EDITOR_DRAFT_KEY)
    if not selected_id:
        st.session_state[MOCK_SERVER_EDITOR_DRAFT_KEY] = None
        return
    if isinstance(current_draft, dict) and str(current_draft.get("id") or "") == selected_id:
        return
    server_item = _find_server_by_id(selected_id)
    if not isinstance(server_item, dict):
        st.session_state[MOCK_SERVER_EDITOR_DRAFT_KEY] = None
        return
    st.session_state[MOCK_SERVER_EDITOR_DRAFT_KEY] = _build_server_draft(server_item)
    st.session_state[MOCK_SERVER_EDITOR_NONCE_KEY] = int(
        st.session_state.get(MOCK_SERVER_EDITOR_NONCE_KEY, 0)
    ) + 1


def _persist_draft(*, should_rerun: bool):
    draft = st.session_state.get(MOCK_SERVER_EDITOR_DRAFT_KEY)
    if not isinstance(draft, dict):
        st.error("Nessun mock server selezionato.")
        return

    validation_error = _validate_draft(draft)
    if validation_error:
        st.error(validation_error)
        return

    try:
        update_mock_server(_server_payload(draft))
    except Exception as exc:
        st.error(f"Errore aggiornamento mock server: {str(exc)}")
        return

    load_mock_servers(force=True)
    refreshed = _find_server_by_id(str(draft.get("id") or ""))
    if isinstance(refreshed, dict):
        st.session_state[MOCK_SERVER_EDITOR_DRAFT_KEY] = _build_server_draft(refreshed)
    st.session_state[MOCK_SERVER_EDITOR_FEEDBACK_KEY] = "Mock server aggiornato."
    st.session_state[MOCK_SERVER_EDITOR_NONCE_KEY] = int(
        st.session_state.get(MOCK_SERVER_EDITOR_NONCE_KEY, 0)
    ) + 1
    if should_rerun:
        st.rerun()


def _persist_draft_after_change():
    _persist_draft(should_rerun=True)


def _load_queue_options() -> tuple[list[dict], dict[str, dict]]:
    load_step_editor_brokers(force=False)
    brokers = st.session_state.get(STEP_EDITOR_BROKERS_KEY, [])
    if not isinstance(brokers, list):
        brokers = []

    queue_options: list[dict] = []
    queue_by_id: dict[str, dict] = {}
    for broker in brokers:
        if not isinstance(broker, dict):
            continue
        broker_id = str(broker.get("id") or "").strip()
        if not broker_id:
            continue
        broker_label = str(broker.get("description") or broker.get("code") or broker_id)
        queues = load_step_editor_queues_for_broker(broker_id, force=False)
        if not isinstance(queues, list):
            continue
        for queue in queues:
            if not isinstance(queue, dict):
                continue
            queue_id = str(queue.get("id") or "").strip()
            if not queue_id:
                continue
            queue_label = str(queue.get("description") or queue.get("code") or queue_id)
            option = {
                "broker_id": broker_id,
                "broker_label": broker_label,
                "queue_id": queue_id,
                "queue_label": queue_label,
                "display": f"{broker_label} | {queue_label}",
            }
            queue_options.append(option)
            queue_by_id[queue_id] = option
    return queue_options, queue_by_id


def _open_add_operation_dialog(target_ui_key: str):
    if not target_ui_key:
        return
    st.session_state[ADD_STEP_OPERATION_DIALOG_OPEN_KEY] = True
    st.session_state[ADD_STEP_OPERATION_DIALOG_TARGET_STEP_UI_KEY] = target_ui_key
    st.session_state[ADD_STEP_OPERATION_DIALOG_NONCE_KEY] = int(
        st.session_state.get(ADD_STEP_OPERATION_DIALOG_NONCE_KEY, 0)
    ) + 1


def _close_add_operation_dialog():
    st.session_state[ADD_STEP_OPERATION_DIALOG_OPEN_KEY] = False
    st.session_state.pop(ADD_STEP_OPERATION_DIALOG_TARGET_STEP_UI_KEY, None)


@st.dialog("Add operation", width="large")
def _add_operation_dialog(
    draft: dict,
    operation_catalog: list[dict],
    operation_labels_by_id: dict[str, str],
):
    pseudo_draft = {
        "steps": [
            item
            for item in (draft.get("apis") or []) + (draft.get("queues") or [])
            if isinstance(item, dict)
        ]
    }
    render_add_step_operation_dialog(
        pseudo_draft,
        operation_catalog,
        operation_labels_by_id,
        _close_add_operation_dialog,
        persist_scenario_changes_fn=_persist_draft_after_change,
    )


@st.dialog("Add API", width="medium")
def _add_api_dialog():
    draft = st.session_state.get(MOCK_SERVER_EDITOR_DRAFT_KEY)
    if not isinstance(draft, dict):
        st.error("Mock server non disponibile.")
        return

    dialog_key = str(draft.get("id") or _new_ui_key())
    st.text_input("Code", key=f"mock_server_add_api_code_{dialog_key}")
    st.text_input("Description", key=f"mock_server_add_api_desc_{dialog_key}")
    method = st.selectbox(
        "Method",
        options=HTTP_METHOD_OPTIONS,
        key=f"mock_server_add_api_method_{dialog_key}",
    )
    path = st.text_input(
        "Path",
        key=f"mock_server_add_api_path_{dialog_key}",
        placeholder="/orders",
    )
    if st.button(
        "Add",
        key=f"mock_server_add_api_submit_{dialog_key}",
        icon=":material/add:",
        use_container_width=True,
    ):
        code = str(st.session_state.get(f"mock_server_add_api_code_{dialog_key}") or "").strip()
        if not code:
            st.error("Il campo Code e' obbligatorio.")
            return
        new_api = {
            "id": None,
            "order": len(draft.get("apis") or []) + 1,
            "code": code,
            "description": str(st.session_state.get(f"mock_server_add_api_desc_{dialog_key}") or ""),
            "method": str(method or "GET"),
            "path": _normalize_path(path),
            "configuration_json": {
                "method": str(method or "GET"),
                "path": _normalize_path(path),
                "params": {},
                "authorization": {},
                "headers": {},
                "body": None,
                "body_match": "contains",
                "response_status": 200,
                "response_headers": {"Content-Type": "application/json"},
                "response_body": {"status": "ok"},
                "priority": 0,
            },
            "operations": [],
            "_ui_key": _new_ui_key(),
        }
        draft.setdefault("apis", []).append(new_api)
        _persist_draft(should_rerun=True)


@st.dialog("Edit API", width="medium")
def _edit_api_dialog(api_entry: dict, api_idx: int):
    draft = st.session_state.get(MOCK_SERVER_EDITOR_DRAFT_KEY)
    if not isinstance(draft, dict):
        st.error("Mock server non disponibile.")
        return
    api_ui_key = str(api_entry.get("_ui_key") or _new_ui_key())
    st.number_input(
        "Order",
        min_value=1,
        step=1,
        key=f"mock_server_edit_api_order_{api_ui_key}",
        value=max(_safe_int(api_entry.get("order"), api_idx + 1), 1),
    )
    st.text_input(
        "Code",
        key=f"mock_server_edit_api_code_{api_ui_key}",
        value=str(api_entry.get("code") or ""),
    )
    st.text_input(
        "Description",
        key=f"mock_server_edit_api_desc_{api_ui_key}",
        value=str(api_entry.get("description") or ""),
    )
    action_cols = st.columns([1, 1], gap="small", vertical_alignment="center")
    with action_cols[0]:
        if st.button(
            "Save",
            key=f"mock_server_edit_api_save_{api_ui_key}",
            icon=":material/save:",
            use_container_width=True,
        ):
            api_entry["order"] = int(
                st.session_state.get(f"mock_server_edit_api_order_{api_ui_key}") or api_idx + 1
            )
            api_entry["code"] = str(
                st.session_state.get(f"mock_server_edit_api_code_{api_ui_key}") or ""
            ).strip()
            api_entry["description"] = str(
                st.session_state.get(f"mock_server_edit_api_desc_{api_ui_key}") or ""
            )
            draft["apis"] = sorted(
                draft.get("apis") or [],
                key=lambda item: _safe_int(item.get("order"), 0),
            )
            _persist_draft(should_rerun=True)
    with action_cols[1]:
        if st.button(
            "Delete",
            key=f"mock_server_edit_api_delete_{api_ui_key}",
            icon=":material/delete:",
            use_container_width=True,
        ):
            apis = draft.get("apis") or []
            if 0 <= api_idx < len(apis):
                apis.pop(api_idx)
            _persist_draft(should_rerun=True)


@st.dialog("Add Queue", width="medium")
def _add_queue_dialog():
    draft = st.session_state.get(MOCK_SERVER_EDITOR_DRAFT_KEY)
    if not isinstance(draft, dict):
        st.error("Mock server non disponibile.")
        return
    queue_options, _ = _load_queue_options()
    option_ids = [str(item.get("queue_id") or "") for item in queue_options if item.get("queue_id")]
    option_by_id = {str(item.get("queue_id")): item for item in queue_options if item.get("queue_id")}

    dialog_key = str(draft.get("id") or _new_ui_key())
    st.text_input("Code", key=f"mock_server_add_queue_code_{dialog_key}")
    st.text_input("Description", key=f"mock_server_add_queue_desc_{dialog_key}")
    selected_queue_id = st.selectbox(
        "Queue",
        options=option_ids or [""],
        key=f"mock_server_add_queue_select_{dialog_key}",
        format_func=lambda queue_id: (
            option_by_id.get(queue_id, {}).get("display")
            if queue_id
            else "Nessuna queue disponibile"
        ),
    )
    if st.button(
        "Add",
        key=f"mock_server_add_queue_submit_{dialog_key}",
        icon=":material/add:",
        use_container_width=True,
    ):
        code = str(st.session_state.get(f"mock_server_add_queue_code_{dialog_key}") or "").strip()
        if not code:
            st.error("Il campo Code e' obbligatorio.")
            return
        if not str(selected_queue_id or "").strip():
            st.error("Seleziona una queue.")
            return
        draft.setdefault("queues", []).append(
            {
                "id": None,
                "order": len(draft.get("queues") or []) + 1,
                "code": code,
                "description": str(st.session_state.get(f"mock_server_add_queue_desc_{dialog_key}") or ""),
                "queue_id": str(selected_queue_id),
                "configuration_json": {
                    "polling_interval_seconds": 1,
                    "max_messages": 10,
                },
                "operations": [],
                "_ui_key": _new_ui_key(),
            }
        )
        _persist_draft(should_rerun=True)


@st.dialog("Edit Queue", width="medium")
def _edit_queue_dialog(queue_entry: dict, queue_idx: int):
    draft = st.session_state.get(MOCK_SERVER_EDITOR_DRAFT_KEY)
    if not isinstance(draft, dict):
        st.error("Mock server non disponibile.")
        return
    queue_options, _ = _load_queue_options()
    option_ids = [str(item.get("queue_id") or "") for item in queue_options if item.get("queue_id")]
    option_by_id = {str(item.get("queue_id")): item for item in queue_options if item.get("queue_id")}

    queue_ui_key = str(queue_entry.get("_ui_key") or _new_ui_key())
    st.number_input(
        "Order",
        min_value=1,
        step=1,
        key=f"mock_server_edit_queue_order_{queue_ui_key}",
        value=max(_safe_int(queue_entry.get("order"), queue_idx + 1), 1),
    )
    st.text_input(
        "Code",
        key=f"mock_server_edit_queue_code_{queue_ui_key}",
        value=str(queue_entry.get("code") or ""),
    )
    st.text_input(
        "Description",
        key=f"mock_server_edit_queue_desc_{queue_ui_key}",
        value=str(queue_entry.get("description") or ""),
    )
    current_queue_id = str(queue_entry.get("queue_id") or "").strip()
    if current_queue_id and current_queue_id not in option_ids:
        option_ids = [current_queue_id, *option_ids]
    selected_queue_id = st.selectbox(
        "Queue",
        options=option_ids or [""],
        key=f"mock_server_edit_queue_select_{queue_ui_key}",
        index=(option_ids.index(current_queue_id) if current_queue_id in option_ids else 0),
        format_func=lambda queue_id: (
            option_by_id.get(queue_id, {}).get("display")
            if queue_id
            else "Nessuna queue disponibile"
        ),
    )
    action_cols = st.columns([1, 1], gap="small", vertical_alignment="center")
    with action_cols[0]:
        if st.button(
            "Save",
            key=f"mock_server_edit_queue_save_{queue_ui_key}",
            icon=":material/save:",
            use_container_width=True,
        ):
            queue_entry["order"] = int(
                st.session_state.get(f"mock_server_edit_queue_order_{queue_ui_key}") or queue_idx + 1
            )
            queue_entry["code"] = str(
                st.session_state.get(f"mock_server_edit_queue_code_{queue_ui_key}") or ""
            ).strip()
            queue_entry["description"] = str(
                st.session_state.get(f"mock_server_edit_queue_desc_{queue_ui_key}") or ""
            )
            queue_entry["queue_id"] = str(selected_queue_id or "").strip()
            draft["queues"] = sorted(
                draft.get("queues") or [],
                key=lambda item: _safe_int(item.get("order"), 0),
            )
            _persist_draft(should_rerun=True)
    with action_cols[1]:
        if st.button(
            "Delete",
            key=f"mock_server_edit_queue_delete_{queue_ui_key}",
            icon=":material/delete:",
            use_container_width=True,
        ):
            queues = draft.get("queues") or []
            if 0 <= queue_idx < len(queues):
                queues.pop(queue_idx)
            _persist_draft(should_rerun=True)


def _render_api_editor(api_entry: dict, api_idx: int, nonce: int):
    api_ui_key = str(api_entry.get("_ui_key") or _new_ui_key())
    api_entry["_ui_key"] = api_ui_key

    code = str(api_entry.get("code") or "").strip()
    description = str(api_entry.get("description") or "").strip()
    label = (
        f"{description} [{code}]"
        if description and code and description != code
        else (description or code or f"API {api_idx + 1}")
    )

    wrapper_cols = st.columns([18, 1], gap="small", vertical_alignment="top")
    with wrapper_cols[0]:
        with st.expander(label, expanded=False):
            cfg = api_entry.get("configuration_json") if isinstance(api_entry.get("configuration_json"), dict) else {}
            method_key = f"mock_server_api_method_{api_ui_key}_{nonce}"
            path_key = f"mock_server_api_path_{api_ui_key}_{nonce}"
            params_key = f"mock_server_api_params_{api_ui_key}_{nonce}"
            auth_key = f"mock_server_api_auth_{api_ui_key}_{nonce}"
            headers_key = f"mock_server_api_headers_{api_ui_key}_{nonce}"
            body_key = f"mock_server_api_body_{api_ui_key}_{nonce}"
            status_key = f"mock_server_api_status_{api_ui_key}_{nonce}"
            response_headers_key = f"mock_server_api_response_headers_{api_ui_key}_{nonce}"
            response_body_key = f"mock_server_api_response_body_{api_ui_key}_{nonce}"

            if method_key not in st.session_state:
                st.session_state[method_key] = str(cfg.get("method") or api_entry.get("method") or "GET")
            if path_key not in st.session_state:
                st.session_state[path_key] = _normalize_path(cfg.get("path") or api_entry.get("path"))
            if params_key not in st.session_state:
                st.session_state[params_key] = _pretty_json(cfg.get("params") or {})
            if auth_key not in st.session_state:
                st.session_state[auth_key] = _pretty_json(cfg.get("authorization") or {})
            if headers_key not in st.session_state:
                st.session_state[headers_key] = _pretty_json(cfg.get("headers") or {})
            if body_key not in st.session_state:
                st.session_state[body_key] = _pretty_json(cfg.get("body"))
            if status_key not in st.session_state:
                st.session_state[status_key] = int(cfg.get("response_status") or 200)
            if response_headers_key not in st.session_state:
                st.session_state[response_headers_key] = _pretty_json(cfg.get("response_headers") or {})
            if response_body_key not in st.session_state:
                st.session_state[response_body_key] = _pretty_json(cfg.get("response_body"))

            conf_cols = st.columns([2, 5], gap="small", vertical_alignment="center")
            with conf_cols[0]:
                selected_method = st.selectbox(
                    "Method",
                    options=HTTP_METHOD_OPTIONS,
                    key=method_key,
                )
            with conf_cols[1]:
                selected_path = st.text_input(
                    "URL path",
                    key=path_key,
                    placeholder="/orders",
                )

            tab_params, tab_auth, tab_headers, tab_body = st.tabs(
                ["Params", "Authorization", "Headers", "Body"]
            )
            with tab_params:
                st.text_area(
                    "Params (JSON)",
                    key=params_key,
                    height=160,
                )
            with tab_auth:
                st.text_area(
                    "Authorization (JSON)",
                    key=auth_key,
                    height=160,
                )
            with tab_headers:
                st.text_area(
                    "Headers (JSON)",
                    key=headers_key,
                    height=160,
                )
            with tab_body:
                st.text_area(
                    "Body (JSON or string)",
                    key=body_key,
                    height=160,
                )
                st.number_input(
                    "Response status",
                    min_value=100,
                    max_value=599,
                    key=status_key,
                )
                st.text_area(
                    "Response headers (JSON)",
                    key=response_headers_key,
                    height=120,
                )
                st.text_area(
                    "Response body (JSON or string)",
                    key=response_body_key,
                    height=120,
                )

            save_cols = st.columns([6, 2], gap="small", vertical_alignment="center")
            with save_cols[1]:
                if st.button(
                    "Save API",
                    key=f"mock_server_save_api_{api_ui_key}_{nonce}",
                    icon=":material/save:",
                    use_container_width=True,
                ):
                    params_value, params_error = _parse_json_dict(
                        st.session_state.get(params_key),
                        field_label="Params",
                        allow_empty=True,
                    )
                    if params_error:
                        st.error(params_error)
                        return
                    auth_value, auth_error = _parse_json_dict(
                        st.session_state.get(auth_key),
                        field_label="Authorization",
                        allow_empty=True,
                    )
                    if auth_error:
                        st.error(auth_error)
                        return
                    headers_value, headers_error = _parse_json_dict(
                        st.session_state.get(headers_key),
                        field_label="Headers",
                        allow_empty=True,
                    )
                    if headers_error:
                        st.error(headers_error)
                        return
                    response_headers_value, response_headers_error = _parse_json_dict(
                        st.session_state.get(response_headers_key),
                        field_label="Response headers",
                        allow_empty=True,
                    )
                    if response_headers_error:
                        st.error(response_headers_error)
                        return

                    api_entry["method"] = str(selected_method or "GET").upper()
                    api_entry["path"] = _normalize_path(selected_path)
                    current_cfg = (
                        api_entry.get("configuration_json")
                        if isinstance(api_entry.get("configuration_json"), dict)
                        else {}
                    )
                    api_entry["configuration_json"] = {
                        **current_cfg,
                        "method": api_entry["method"],
                        "path": api_entry["path"],
                        "params": params_value or {},
                        "authorization": auth_value or {},
                        "headers": headers_value or {},
                        "body": _parse_json_body(st.session_state.get(body_key) or ""),
                        "response_status": int(st.session_state.get(status_key) or 200),
                        "response_headers": response_headers_value or {},
                        "response_body": _parse_json_body(
                            st.session_state.get(response_body_key) or ""
                        ),
                    }
                    _persist_draft(should_rerun=True)

            st.divider()
            st.markdown("**Operations**")
            operations = api_entry.get("operations") or []
            for op_idx, operation in enumerate(operations):
                render_operation_component(
                    api_entry,
                    operation,
                    op_idx,
                    api_ui_key,
                    nonce,
                    persist_scenario_changes_fn=_persist_draft_after_change,
                )

            add_op_cols = st.columns([8, 2], gap="small", vertical_alignment="center")
            with add_op_cols[1]:
                if st.button(
                    "Add operation",
                    key=f"mock_server_add_api_operation_{api_ui_key}_{nonce}",
                    icon=":material/add:",
                    use_container_width=True,
                ):
                    _open_add_operation_dialog(api_ui_key)
                    st.rerun()
    with wrapper_cols[1]:
        if st.button(
            "",
            key=f"mock_server_edit_api_btn_{api_ui_key}_{nonce}",
            icon=":material/more_vert:",
            help="Edit/Delete API",
            type="tertiary",
            use_container_width=True,
        ):
            _edit_api_dialog(api_entry, api_idx)


def _render_queue_editor(
    queue_entry: dict,
    queue_idx: int,
    queue_by_id: dict[str, dict],
    nonce: int,
):
    queue_ui_key = str(queue_entry.get("_ui_key") or _new_ui_key())
    queue_entry["_ui_key"] = queue_ui_key

    code = str(queue_entry.get("code") or "").strip()
    description = str(queue_entry.get("description") or "").strip()
    label = (
        f"{description} [{code}]"
        if description and code and description != code
        else (description or code or f"Queue {queue_idx + 1}")
    )

    queue_id = str(queue_entry.get("queue_id") or "").strip()
    queue_item = queue_by_id.get(queue_id) or {}
    broker_label = str(queue_item.get("broker_label") or "-")
    queue_label = str(queue_item.get("queue_label") or queue_id or "-")

    wrapper_cols = st.columns([18, 1], gap="small", vertical_alignment="top")
    with wrapper_cols[0]:
        with st.expander(label, expanded=False):
            st.markdown(f"**Broker:** {broker_label}")
            st.markdown(f"**Queue:** {queue_label}")
            st.divider()
            st.markdown("**Operations**")
            operations = queue_entry.get("operations") or []
            for op_idx, operation in enumerate(operations):
                render_operation_component(
                    queue_entry,
                    operation,
                    op_idx,
                    queue_ui_key,
                    nonce,
                    persist_scenario_changes_fn=_persist_draft_after_change,
                )
            add_op_cols = st.columns([8, 2], gap="small", vertical_alignment="center")
            with add_op_cols[1]:
                if st.button(
                    "Add operation",
                    key=f"mock_server_add_queue_operation_{queue_ui_key}_{nonce}",
                    icon=":material/add:",
                    use_container_width=True,
                ):
                    _open_add_operation_dialog(queue_ui_key)
                    st.rerun()
    with wrapper_cols[1]:
        if st.button(
            "",
            key=f"mock_server_edit_queue_btn_{queue_ui_key}_{nonce}",
            icon=":material/more_vert:",
            help="Edit/Delete queue binding",
            type="tertiary",
            use_container_width=True,
        ):
            _edit_queue_dialog(queue_entry, queue_idx)


def _render_feedback():
    message = st.session_state.pop(MOCK_SERVER_EDITOR_FEEDBACK_KEY, None)
    if message:
        st.success(str(message), icon=":material/check_circle:")


def _render_editor():
    _ensure_editor_draft()
    draft = st.session_state.get(MOCK_SERVER_EDITOR_DRAFT_KEY)
    if not isinstance(draft, dict):
        st.info("Nessun mock server selezionato.")
        if st.button(
            "Back to Mock Servers",
            icon=":material/arrow_back:",
            use_container_width=False,
        ):
            st.switch_page(MOCK_SERVERS_PAGE_PATH)
        _render_feedback()
        return

    load_operations_catalog(force=False)
    operation_catalog = st.session_state.get(OPERATIONS_CATALOG_KEY, [])
    if not isinstance(operation_catalog, list):
        operation_catalog = []
    operation_labels_by_id = {
        str(item.get("id")): (
            f"{item.get('code') or '-'} ({item.get('description') or '-'})"
        )
        for item in operation_catalog
        if isinstance(item, dict) and item.get("id")
    }

    _, queue_by_id = _load_queue_options()

    header_cols = st.columns([8, 2], gap="small", vertical_alignment="center")
    with header_cols[1]:
        if st.button(
            "Back",
            key="mock_server_editor_back_btn",
            icon=":material/arrow_back:",
            use_container_width=True,
        ):
            st.switch_page(MOCK_SERVERS_PAGE_PATH)

    description = str(draft.get("description") or draft.get("code") or "-")
    endpoint = _normalize_endpoint(draft.get("endpoint"))
    st.title(description)
    st.subheader(f"/mock/{endpoint or '-'}")

    toggle_value = st.toggle(
        "Active",
        key=f"mock_server_editor_active_toggle_{draft.get('id')}",
        value=bool(draft.get("is_active")),
    )
    if toggle_value != bool(draft.get("is_active")):
        try:
            if toggle_value:
                activate_mock_server(str(draft.get("id") or ""))
            else:
                deactivate_mock_server(str(draft.get("id") or ""))
        except Exception as exc:
            st.error(f"Errore aggiornamento stato mock server: {str(exc)}")
        else:
            load_mock_servers(force=True)
            refreshed = _find_server_by_id(str(draft.get("id") or ""))
            if isinstance(refreshed, dict):
                st.session_state[MOCK_SERVER_EDITOR_DRAFT_KEY] = _build_server_draft(refreshed)
            st.session_state[MOCK_SERVER_EDITOR_FEEDBACK_KEY] = (
                "Mock server attivato." if toggle_value else "Mock server disattivato."
            )
            st.rerun()

    st.divider()
    api_header_cols = st.columns([8, 2], gap="small", vertical_alignment="center")
    with api_header_cols[0]:
        st.subheader("APIs")
    with api_header_cols[1]:
        if st.button(
            "Add API",
            key=f"mock_server_editor_add_api_{draft.get('id')}",
            icon=":material/add:",
            use_container_width=True,
        ):
            _add_api_dialog()

    apis = draft.get("apis") or []
    if not apis:
        st.caption("Nessuna API configurata.")
    nonce = int(st.session_state.get(MOCK_SERVER_EDITOR_NONCE_KEY, 0))
    for api_idx, api_entry in enumerate(apis):
        if not isinstance(api_entry, dict):
            continue
        _render_api_editor(api_entry, api_idx, nonce)

    st.divider()
    queue_header_cols = st.columns([8, 2], gap="small", vertical_alignment="center")
    with queue_header_cols[0]:
        st.subheader("Queues")
    with queue_header_cols[1]:
        if st.button(
            "Add Queue",
            key=f"mock_server_editor_add_queue_{draft.get('id')}",
            icon=":material/add:",
            use_container_width=True,
        ):
            _add_queue_dialog()

    queues = draft.get("queues") or []
    if not queues:
        st.caption("Nessuna queue configurata.")
    for queue_idx, queue_entry in enumerate(queues):
        if not isinstance(queue_entry, dict):
            continue
        _render_queue_editor(queue_entry, queue_idx, queue_by_id, nonce)

    if st.session_state.get(ADD_STEP_OPERATION_DIALOG_OPEN_KEY, False):
        _add_operation_dialog(draft, operation_catalog, operation_labels_by_id)
    _render_feedback()


def render_mock_server_editor_page():
    _render_editor()
