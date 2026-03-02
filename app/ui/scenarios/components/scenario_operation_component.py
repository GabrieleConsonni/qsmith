import json
from decimal import Decimal
from uuid import uuid4

import streamlit as st

from database_connections.services.data_loader_service import (
    DATABASE_CONNECTIONS_KEY,
    load_database_connections,
)
from scenarios.services.data_loader_service import (
    load_operations_catalog,
    load_step_editor_context,
    load_step_editor_queues_for_broker,
)
from scenarios.services.scenario_api_service import (
    create_operation,
    delete_operation_by_id,
    get_operations_page,
)
from scenarios.services.state_keys import (
    ADD_STEP_OPERATION_DIALOG_NONCE_KEY,
    ADD_STEP_OPERATION_DIALOG_TARGET_STEP_UI_KEY,
    OPERATIONS_CATALOG_KEY,
    SCENARIO_FEEDBACK_KEY,
    STEP_EDITOR_BROKERS_KEY,
)

OPERATION_TYPE_PUBLISH = "publish"
OPERATION_TYPE_SAVE_INTERNAL_DB = "save-internal-db"
OPERATION_TYPE_SAVE_EXTERNAL_DB = "save-external-db"
OPERATION_TYPE_OPTIONS = [
    OPERATION_TYPE_PUBLISH,
    OPERATION_TYPE_SAVE_INTERNAL_DB,
    OPERATION_TYPE_SAVE_EXTERNAL_DB,
]
OPERATION_STATUS_SUCCESS = "success"
OPERATION_STATUS_ERROR = "error"
OPERATION_STATUS_RUNNING = "running"
OPERATION_STATUS_IDLE = "idle"
OPERATION_PAGE_SIZE = 5


def _safe_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, Decimal):
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


def _new_ui_key() -> str:
    return uuid4().hex[:10]


def _operation_type_label(operation_type: str) -> str:
    labels = {
        OPERATION_TYPE_PUBLISH: "publish",
        OPERATION_TYPE_SAVE_INTERNAL_DB: "save-internal-db",
        OPERATION_TYPE_SAVE_EXTERNAL_DB: "save-external-db",
    }
    return labels.get(operation_type, operation_type or "-")


def _broker_label(broker_item: dict) -> str:
    return str(broker_item.get("description") or broker_item.get("code") or "-")


def _queue_label(queue_item: dict) -> str:
    return str(queue_item.get("description") or queue_item.get("code") or "-")


def _normalize_select_key(key: str, options: list[str]):
    if not key:
        return
    if not options:
        st.session_state[key] = ""
        return
    current_value = str(st.session_state.get(key) or "")
    if current_value not in options:
        st.session_state[key] = options[0]


def _pretty_json(value: object) -> str:
    return json.dumps(value, indent=2, ensure_ascii=True)


def _safe_dict(value: object) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {}
    return {}


def _safe_list(value: object) -> list[dict]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _map_by_id(items: list[dict]) -> dict[str, dict]:
    return {str(item.get("id")): item for item in items if item.get("id")}


def _resolve_configuration_value(configuration_json: dict, *keys: str):
    for key in keys:
        value = configuration_json.get(key)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None

def _connection_label(connection_item: dict) -> str:
    return str(connection_item.get("description") or connection_item.get("code") or "-")


def _reload_step_operations(scenario_step: dict):
    operations = scenario_step.get("operations")
    if not isinstance(operations, list):
        return
    indexed_operations = list(enumerate(operations))
    indexed_operations.sort(
        key=lambda item: (_safe_int(item[1].get("order"), item[0] + 1), item[0])
    )
    scenario_step["operations"] = [operation for _, operation in indexed_operations]


def _persist_scenario_changes(persist_scenario_changes_fn=None):
    if callable(persist_scenario_changes_fn):
        persist_scenario_changes_fn()
        return
    st.rerun()


def _find_queue_and_broker_by_queue_id(
    queue_id: str,
    brokers_by_id: dict[str, dict],
) -> tuple[dict, dict]:
    queue_id_value = str(queue_id or "").strip()
    if not queue_id_value:
        return {}, {}

    def _find_queue_in_items(items: list[dict], target_queue_id: str) -> dict:
        return next(
            (
                item
                for item in items
                if str(item.get("id") or "").strip() == target_queue_id
            ),
            {},
        )

    for current_broker_id, broker_item in brokers_by_id.items():
        queues = load_step_editor_queues_for_broker(str(current_broker_id), force=False)
        queue_item = _find_queue_in_items(queues, queue_id_value)
        if queue_item:
            return queue_item, broker_item

    return {}, {}


def _render_operation_details(operation_item: dict):
    if not isinstance(operation_item, dict):
        st.caption("Operation non trovata nel catalogo.")
        return

    operation_type = str(operation_item.get("operation_type") or "").strip()
    configuration_json = _safe_dict(operation_item.get("configuration_json") or {})

    if operation_type == OPERATION_TYPE_PUBLISH:
        load_step_editor_context(force=False)
        brokers = _safe_list(st.session_state.get(STEP_EDITOR_BROKERS_KEY, []))
        brokers_by_id = _map_by_id(brokers)
        queue_id = str(
            _resolve_configuration_value(configuration_json, "queue_id", "queueId") or ""
        ).strip()
        queue_item, broker_item = _find_queue_and_broker_by_queue_id(queue_id, brokers_by_id)
        queue_label = str(queue_item.get("description") or queue_item.get("code") or queue_id or "-")
        broker_label = str(broker_item.get("description") or broker_item.get("code") or "-")
        st.write(f"Queue: {queue_label} [ {broker_label} ]")
        return

    if operation_type == OPERATION_TYPE_SAVE_INTERNAL_DB:
        table_name = str(
            _resolve_configuration_value(configuration_json, "table_name", "tableName") or "-"
        ).strip()
        st.write(f"Table: {table_name or '-'}")
        return

    if operation_type == OPERATION_TYPE_SAVE_EXTERNAL_DB:
        load_database_connections(force=False)
        connections = _safe_list(st.session_state.get(DATABASE_CONNECTIONS_KEY, []))
        connections_by_id = _map_by_id(connections)
        connection_id = str(
            _resolve_configuration_value(
                configuration_json,
                "connection_id",
                "connectionId",
                "dataset_id",
            )
            or ""
        ).strip()
        connection_item = connections_by_id.get(connection_id, {})
        table_name = str(
            _resolve_configuration_value(configuration_json, "table_name", "tableName") or "-"
        ).strip()
        connection_label = _connection_label(connection_item)
        if connection_label == "-" and connection_id:
            connection_label = connection_id
        st.write(f"Connection: {connection_label}")
        st.write(f"Table: {table_name or '-'}")
        return

    st.code(_pretty_json(configuration_json), language="json")


def _new_draft_operation(
    code: str = "",
    description: str = "",
    operation_type: str = OPERATION_TYPE_PUBLISH,
    configuration_json: dict | None = None,
    order: int = 1,
) -> dict:
    return {
        "id": None,
        "order": order,
        "code": str(code or "").strip(),
        "description": str(description or ""),
        "operation_type": str(operation_type or OPERATION_TYPE_PUBLISH),
        "configuration_json": configuration_json if isinstance(configuration_json, dict) else {},
        "_ui_key": _new_ui_key(),
    }


def _extract_operation_draft_fields(operation_item: dict) -> tuple[str, str, str, dict]:
    cfg = operation_item.get("configuration_json")
    if not isinstance(cfg, dict):
        cfg = {}
    operation_type = str(
        operation_item.get("operation_type") or cfg.get("operationType") or ""
    ).strip().replace("_", "-").lower()
    return (
        str(operation_item.get("code") or "").strip(),
        str(operation_item.get("description") or ""),
        operation_type or OPERATION_TYPE_PUBLISH,
        cfg,
    )


@st.dialog("Modify operation", width="large")
def _edit_step_operation_dialog(
    scenario_step: dict,
    operation: dict,
    op_idx: int,
    step_ui_key: str,
    nonce: int,
    persist_scenario_changes_fn=None,
):
    operation_ui_key = operation.get("_ui_key") or f"{step_ui_key}_op_{op_idx}"
    operation["_ui_key"] = operation_ui_key
    selected_order = int(
        st.number_input(
            "Operation order",
            min_value=0,
            value=_safe_int(operation.get("order"), op_idx + 1),
            key=f"scenario_{nonce}_step_{step_ui_key}_operation_order_{operation_ui_key}",
        )
    )

    action_cols = st.columns([4, 2, 2, 2], gap="small", vertical_alignment="center")
    with action_cols[1]:
        if st.button(
            "Save",
            key=f"scenario_{nonce}_step_{step_ui_key}_operation_edit_save_{operation_ui_key}",
            icon=":material/save:",
            type="secondary",
            use_container_width=True,
        ):
            operation["order"] = selected_order
            _reload_step_operations(scenario_step)
            _persist_scenario_changes(persist_scenario_changes_fn)
    with action_cols[2]:
        if st.button(
            "Delete",
            key=f"scenario_{nonce}_step_{step_ui_key}_operation_edit_delete_{operation_ui_key}",
            icon=":material/delete:",
            type="secondary",
            use_container_width=True,
        ):
            operations = scenario_step.get("operations", [])
            if 0 <= op_idx < len(operations):
                operations.pop(op_idx)
            _persist_scenario_changes(persist_scenario_changes_fn)
    with action_cols[3]:
        if st.button(
            "Cancel",
            key=f"scenario_{nonce}_step_{step_ui_key}_operation_edit_cancel_{operation_ui_key}",
            use_container_width=True,
        ):
            st.rerun()

def _operation_status_icon(operation_status: str) -> str:
    normalized_status = str(operation_status or "").strip().lower()
    if normalized_status == OPERATION_STATUS_SUCCESS:
        return ":material/check_circle:"
    if normalized_status == OPERATION_STATUS_ERROR:
        return ":material/error:"
    if normalized_status == OPERATION_STATUS_RUNNING:
        return ":material/pending:"
    return ":material/radio_button_unchecked:"

def render_operation_component(
    scenario_step: dict,
    operation: dict,
    op_idx: int,
    step_ui_key: str,
    nonce: int,
    operation_status: str = OPERATION_STATUS_IDLE,
    operation_error_message: str = "",
    persist_scenario_changes_fn=None,
):
    operation_ui_key = operation.get("_ui_key") or f"{step_ui_key}_op_{op_idx}"
    operation["_ui_key"] = operation_ui_key
    operation_code = str(operation.get("code") or "").strip()
    operation_description = str(operation.get("description") or "").strip()
    operation_label = (
        f"{operation_description} [{operation_code}]"
        if operation_code and operation_description and operation_code != operation_description
        else (operation_description or operation_code or f"Operation {op_idx + 1}")
    )
    operation_type = _operation_type_label(str(operation.get("operation_type") or ""))
    operation_action_cols = st.columns([1, 18, 1], gap="small", vertical_alignment="top")
    with operation_action_cols[0]:
        st.button(
            "",
            key=f"scenario_{nonce}_step_{step_ui_key}_operation_status_{operation_ui_key}",
            icon=_operation_status_icon(operation_status),
            type="tertiary",
            disabled=True,
            use_container_width=True,
        )

    with operation_action_cols[1]:
        with st.container(border=True):
            st.markdown(f"**{operation_label}**")
            st.markdown(f"*{operation_type} operation*")
            _render_operation_details(operation)
            if operation_error_message:
                st.caption(f"Error: {operation_error_message}")
    with operation_action_cols[2]:
        if st.button(
            "",
            key=f"scenario_{nonce}_step_{step_ui_key}_operation_more_actions_{operation_ui_key}",
            icon=":material/more_vert:",
            help="Modify operation",
            type="tertiary",
            use_container_width=True,
        ):
            _edit_step_operation_dialog(
                scenario_step=scenario_step,
                operation=operation,
                op_idx=op_idx,
                step_ui_key=step_ui_key,
                nonce=nonce,
                persist_scenario_changes_fn=persist_scenario_changes_fn,
            )


def find_draft_step_by_ui_key(draft: dict, step_ui_key: str) -> dict | None:
    if not step_ui_key:
        return None
    for scenario_step in draft.get("steps") or []:
        if str(scenario_step.get("_ui_key") or "") == str(step_ui_key):
            return scenario_step
    return None


def append_operation_to_step(scenario_step: dict, operation_item: dict):
    if not isinstance(operation_item, dict):
        return
    code, description, operation_type, cfg = _extract_operation_draft_fields(operation_item)
    if not code:
        return
    operations = scenario_step.setdefault("operations", [])
    operations.append(
        _new_draft_operation(
            code=code,
            description=description,
            operation_type=operation_type,
            configuration_json=cfg,
            order=len(operations) + 1,
        )
    )


def build_operation_creation_payload(dialog_nonce: int) -> tuple[dict | None, str | None]:
    code = str(st.session_state.get(f"scenario_add_operation_code_{dialog_nonce}") or "").strip()
    description = str(
        st.session_state.get(f"scenario_add_operation_description_{dialog_nonce}") or ""
    )
    operation_type = str(
        st.session_state.get(f"scenario_add_operation_type_{dialog_nonce}") or OPERATION_TYPE_PUBLISH
    )
    if not code:
        return None, "Il campo Code dell'operazione e' obbligatorio."

    cfg: dict
    if operation_type == OPERATION_TYPE_PUBLISH:
        queue_id = str(
            st.session_state.get(f"scenario_add_operation_queue_id_{dialog_nonce}") or ""
        ).strip()
        if not queue_id:
            return None, "Il campo Queue id e' obbligatorio."
        cfg = {
            "operationType": OPERATION_TYPE_PUBLISH,
            "queue_id": queue_id,
        }
    elif operation_type == OPERATION_TYPE_SAVE_INTERNAL_DB:
        table_name = str(
            st.session_state.get(f"scenario_add_operation_internal_table_name_{dialog_nonce}")
            or ""
        ).strip()
        if not table_name:
            return None, "Il campo Table name e' obbligatorio."
        cfg = {
            "operationType": OPERATION_TYPE_SAVE_INTERNAL_DB,
            "table_name": table_name,
        }
    elif operation_type == OPERATION_TYPE_SAVE_EXTERNAL_DB:
        connection_id = str(
            st.session_state.get(f"scenario_add_operation_connection_id_{dialog_nonce}") or ""
        ).strip()
        table_name = str(
            st.session_state.get(f"scenario_add_operation_external_table_name_{dialog_nonce}")
            or ""
        ).strip()
        if not connection_id:
            return None, "Il campo Connection e' obbligatorio."
        if not table_name:
            return None, "Il campo Table name e' obbligatorio."
        cfg = {
            "operationType": OPERATION_TYPE_SAVE_EXTERNAL_DB,
            "connection_id": connection_id,
            "table_name": table_name,
        }
    else:
        return None, f"Operation type non supportato: {operation_type}"

    return {
        "code": code,
        "description": description,
        "cfg": cfg,
    }, None


def build_draft_operation_from_creation_payload(payload: dict) -> dict:
    cfg = payload.get("cfg") if isinstance(payload, dict) else {}
    if not isinstance(cfg, dict):
        cfg = {}
    operation_type = str(cfg.get("operationType") or OPERATION_TYPE_PUBLISH).strip().replace("_", "-").lower()
    return {
        "code": str((payload or {}).get("code") or "").strip(),
        "description": str((payload or {}).get("description") or ""),
        "operation_type": operation_type or OPERATION_TYPE_PUBLISH,
        "configuration_json": cfg,
    }


def render_readonly_operation_preview(selected_operation: dict, dialog_nonce: int):
    if not isinstance(selected_operation, dict):
        st.info("Seleziona un'operazione esistente.")
        return

    operation_id = str(selected_operation.get("id") or "")
    st.text_input(
        "Code",
        value=str(selected_operation.get("code") or ""),
        key=f"scenario_add_operation_preview_code_{dialog_nonce}_{operation_id}",
        disabled=True,
    )
    st.text_input(
        "Description",
        value=str(selected_operation.get("description") or ""),
        key=f"scenario_add_operation_preview_description_{dialog_nonce}_{operation_id}",
        disabled=True,
    )
    st.text_input(
        "Operation type",
        value=_operation_type_label(str(selected_operation.get("operation_type") or "")),
        key=f"scenario_add_operation_preview_type_{dialog_nonce}_{operation_id}",
        disabled=True,
    )
    st.text_area(
        "Configuration",
        value=_pretty_json(selected_operation.get("configuration_json") or {}),
        key=f"scenario_add_operation_preview_cfg_{dialog_nonce}_{operation_id}",
        disabled=True,
        height=220,
    )


def _resolve_target_step_for_operation_dialog(
    draft: dict,
    dialog_nonce: int,
    close_add_step_operation_dialog_fn,
) -> dict | None:
    target_step_ui_key = str(
        st.session_state.get(ADD_STEP_OPERATION_DIALOG_TARGET_STEP_UI_KEY) or ""
    )
    scenario_step = find_draft_step_by_ui_key(draft, target_step_ui_key)
    if isinstance(scenario_step, dict):
        return scenario_step

    st.error("Step di destinazione non trovato.")
    if st.button(
        "Cancel",
        key=f"scenario_add_operation_missing_step_cancel_{dialog_nonce}",
        use_container_width=True,
    ):
        close_add_step_operation_dialog_fn()
        st.rerun()
    return None


def _render_existing_operations_panel(
    scenario_step: dict,
    operation_labels_by_id: dict[str, str],
    close_add_step_operation_dialog_fn,
    dialog_nonce: int,
    persist_scenario_changes_fn=None,
    show_title: bool = True,
):
    if show_title:
        st.markdown("**Select existing operation**")
    search_key = f"scenario_add_operation_search_{dialog_nonce}"
    page_key = f"scenario_add_operation_page_{dialog_nonce}"
    last_search_key = f"scenario_add_operation_last_search_{dialog_nonce}"

    search_value = st.text_input(
        "Filter by text/description",
        key=search_key,
        placeholder="Search by code or description",
    ).strip()
    normalized_search = search_value.lower()
    if normalized_search != str(st.session_state.get(last_search_key) or ""):
        st.session_state[last_search_key] = normalized_search
        st.session_state[page_key] = 1

    current_page = max(_safe_int(st.session_state.get(page_key), 1), 1)
    page_payload = get_operations_page(
        current_page,
        size=OPERATION_PAGE_SIZE,
        search=search_value,
    )
    total_pages = max(_safe_int(page_payload.get("total_pages"), 0), 0)
    total_items = max(_safe_int(page_payload.get("total_items"), 0), 0)
    if total_pages > 0 and current_page > total_pages:
        st.session_state[page_key] = total_pages
        st.rerun()

    available_operations = page_payload.get("items") or []
    if not isinstance(available_operations, list):
        available_operations = []

    resolved_page = max(_safe_int(page_payload.get("page"), current_page), 1)

    if total_items <= 0 and search_value:
        st.info("Nessuna operation trovata per il filtro inserito.")
    elif total_items <= 0:
        st.info("Nessuna operation disponibile da selezionare.")

    for op_idx, operation_item in enumerate(available_operations):
        operation_id = str(operation_item.get("id") or "").strip()
        operation_label = operation_labels_by_id.get(operation_id) or (
            f"{operation_item.get('code') or '-'} ({operation_item.get('description') or '-'})"
        )
        with st.expander(operation_label, expanded=False):
            _render_operation_details(operation_item)
            if st.button(
                "Add",
                key=(
                    "scenario_add_operation_select_existing_"
                    f"{dialog_nonce}_{operation_id}_{op_idx}"
                ),
                icon=":material/add:",
                type="secondary",
                use_container_width=True,
            ):
                append_operation_to_step(scenario_step, operation_item)
                close_add_step_operation_dialog_fn()
                st.session_state[SCENARIO_FEEDBACK_KEY] = "Operazione aggiunta."
                _persist_scenario_changes(persist_scenario_changes_fn)
            if st.button(
                "Delete",
                key=f"scenario_add_operation_delete_existing_{dialog_nonce}_{operation_id}_{op_idx}",
                icon=":material/delete:",
                type="secondary",
                use_container_width=True,
                disabled=not bool(operation_id),
            ):
                try:
                    delete_operation_by_id(operation_id)
                except Exception as exc:
                    st.error(f"Errore cancellazione operazione: {str(exc)}")
                    return
                load_operations_catalog(force=True)
                st.session_state[SCENARIO_FEEDBACK_KEY] = "Operazione eliminata da anagrafica."
                st.rerun()

    pagination_cols = st.columns([1, 1, 6], gap="small", vertical_alignment="center")
    with pagination_cols[0]:
        if st.button(
            "",
            key=f"scenario_add_operation_page_prev_{dialog_nonce}",
            icon=":material/keyboard_arrow_left:",
            help="Previous page",
            use_container_width=True,
            disabled=current_page <= 1,
        ):
            st.session_state[page_key] = max(current_page - 1, 1)
            st.rerun()
    with pagination_cols[1]:
        if st.button(
            "",
            key=f"scenario_add_operation_page_next_{dialog_nonce}",
            icon=":material/keyboard_arrow_right:",
            help="Next page",
            use_container_width=True,
            disabled=(total_pages <= 0 or current_page >= total_pages),
        ):
            st.session_state[page_key] = current_page + 1
            st.rerun()
    with pagination_cols[2]:
        if total_items > 0:
            st.caption(
                f"Pagina {resolved_page}/{max(total_pages, 1)} - {total_items} operation trovate"
            )


def _render_new_operation_form_panel(
    scenario_step: dict,
    close_add_step_operation_dialog_fn,
    dialog_nonce: int,
    persist_scenario_changes_fn=None,
):
    load_step_editor_context(force=False)
    load_database_connections(force=False)
    brokers = st.session_state.get(STEP_EDITOR_BROKERS_KEY, [])
    database_connections = st.session_state.get(DATABASE_CONNECTIONS_KEY, [])
    if not isinstance(brokers, list):
        brokers = []
    if not isinstance(database_connections, list):
        database_connections = []

    broker_ids = [str(item.get("id")) for item in brokers if item.get("id")]
    broker_by_id = {str(item.get("id")): item for item in brokers if item.get("id")}
    database_connection_ids = [
        str(item.get("id")) for item in database_connections if item.get("id")
    ]
    database_connection_by_id = {
        str(item.get("id")): item for item in database_connections if item.get("id")
    }

    st.markdown("**Insert new one**")
    st.text_input(
        "Code",
        key=f"scenario_add_operation_code_{dialog_nonce}",
    )
    st.text_input(
        "Description",
        key=f"scenario_add_operation_description_{dialog_nonce}",
    )
    operation_type = st.selectbox(
        "Operation type",
        options=OPERATION_TYPE_OPTIONS,
        format_func=_operation_type_label,
        key=f"scenario_add_operation_type_{dialog_nonce}",
    )

    if operation_type == OPERATION_TYPE_PUBLISH:
        broker_select_key = f"scenario_add_operation_broker_id_{dialog_nonce}"
        _normalize_select_key(broker_select_key, broker_ids or [""])
        selected_broker_id = st.selectbox(
            "Broker",
            options=broker_ids or [""],
            format_func=lambda _id: (
                _broker_label(broker_by_id.get(_id, {}))
                if _id
                else "Nessun broker disponibile"
            ),
            key=broker_select_key,
            disabled=not bool(broker_ids),
        )
        queues = (
            load_step_editor_queues_for_broker(selected_broker_id, force=False)
            if selected_broker_id
            else []
        )
        queue_ids = [str(item.get("id")) for item in queues if item.get("id")]
        queue_by_id = {str(item.get("id")): item for item in queues if item.get("id")}
        queue_select_key = f"scenario_add_operation_queue_id_{dialog_nonce}"
        _normalize_select_key(queue_select_key, queue_ids or [""])
        st.selectbox(
            "Queue",
            options=queue_ids or [""],
            format_func=lambda _id: (
                _queue_label(queue_by_id.get(_id, {}))
                if _id
                else "Nessuna queue disponibile"
            ),
            key=queue_select_key,
            disabled=not bool(queue_ids),
        )
        if not broker_ids:
            st.info("Nessun broker configurato.")
        elif selected_broker_id and not queue_ids:
            st.info("Nessuna queue configurata per il broker selezionato.")
    elif operation_type == OPERATION_TYPE_SAVE_INTERNAL_DB:
        st.text_input(
            "Table name",
            key=f"scenario_add_operation_internal_table_name_{dialog_nonce}",
        )
    elif operation_type == OPERATION_TYPE_SAVE_EXTERNAL_DB:
        connection_select_key = f"scenario_add_operation_connection_id_{dialog_nonce}"
        _normalize_select_key(connection_select_key, database_connection_ids or [""])
        st.selectbox(
            "Connection",
            options=database_connection_ids or [""],
            format_func=lambda _id: (
                _connection_label(database_connection_by_id.get(_id, {}))
                if _id
                else "Nessuna connection disponibile"
            ),
            key=connection_select_key,
            disabled=not bool(database_connection_ids),
        )
        st.text_input(
            "Table name",
            key=f"scenario_add_operation_external_table_name_{dialog_nonce}",
        )
        if not database_connection_ids:
            st.info("Nessuna connection database configurata.")

    create_cols = st.columns([1, 1], gap="small")
    with create_cols[0]:
        if st.button(
            "Save and add",
            key=f"scenario_add_operation_save_and_add_{dialog_nonce}",
            icon=":material/save:",
            type="secondary",
            use_container_width=True,
        ):
            payload, validation_error = build_operation_creation_payload(dialog_nonce)
            if validation_error:
                st.error(validation_error)
                return

            try:
                response = create_operation(payload or {})
            except Exception as exc:
                st.error(f"Errore creazione operazione: {str(exc)}")
                return

            created_operation_id = str(response.get("id") or "").strip()
            if not created_operation_id:
                st.error("Risposta creazione operazione non valida.")
                return

            load_operations_catalog(force=True)
            updated_operations_catalog = st.session_state.get(OPERATIONS_CATALOG_KEY, [])
            if not isinstance(updated_operations_catalog, list):
                updated_operations_catalog = []
            created_operation = next(
                (
                    item
                    for item in updated_operations_catalog
                    if str(item.get("id") or "").strip() == created_operation_id
                ),
                None,
            )
            append_operation_to_step(
                scenario_step,
                created_operation
                if isinstance(created_operation, dict)
                else build_draft_operation_from_creation_payload(payload or {}),
            )
            close_add_step_operation_dialog_fn()
            st.session_state[SCENARIO_FEEDBACK_KEY] = "Nuova operazione creata e aggiunta."
            _persist_scenario_changes(persist_scenario_changes_fn)

    with create_cols[1]:
        if st.button(
            "Add only",
            key=f"scenario_add_operation_add_only_{dialog_nonce}",
            icon=":material/add_circle:",
            type="secondary",
            use_container_width=True,
        ):
            payload, validation_error = build_operation_creation_payload(dialog_nonce)
            if validation_error:
                st.error(validation_error)
                return
            append_operation_to_step(
                scenario_step,
                build_draft_operation_from_creation_payload(payload or {}),
            )
            close_add_step_operation_dialog_fn()
            st.session_state[SCENARIO_FEEDBACK_KEY] = "Nuova step operation aggiunta."
            _persist_scenario_changes(persist_scenario_changes_fn)


def render_add_step_operation_dialog(
    draft: dict,
    operation_catalog: list[dict],
    operation_labels_by_id: dict[str, str],
    close_add_step_operation_dialog_fn,
    persist_scenario_changes_fn=None,
):
    dialog_nonce = int(st.session_state.get(ADD_STEP_OPERATION_DIALOG_NONCE_KEY, 0))
    show_existing_key = f"scenario_add_operation_show_existing_{dialog_nonce}"
    scenario_step = _resolve_target_step_for_operation_dialog(
        draft,
        dialog_nonce,
        close_add_step_operation_dialog_fn,
    )
    if not isinstance(scenario_step, dict):
        return

    _render_new_operation_form_panel(
        scenario_step,
        close_add_step_operation_dialog_fn,
        dialog_nonce,
        persist_scenario_changes_fn=persist_scenario_changes_fn,
    )

    st.divider()
    existing_cols = st.columns([8, 2], gap="small", vertical_alignment="center")
    with existing_cols[0]:
        st.markdown("**Select existing operation**")
    with existing_cols[1]:
        show_existing = bool(st.session_state.get(show_existing_key, False))
        if st.button(
            "Nascondi" if show_existing else "Ricerca",
            key=f"scenario_add_operation_toggle_existing_{dialog_nonce}",
            icon=":material/search:",
            type="secondary",
            use_container_width=True,
        ):
            st.session_state[show_existing_key] = not show_existing
            st.rerun()

    if bool(st.session_state.get(show_existing_key, False)):
        _render_existing_operations_panel(
            scenario_step,
            operation_labels_by_id,
            close_add_step_operation_dialog_fn,
            dialog_nonce,
            persist_scenario_changes_fn=persist_scenario_changes_fn,
            show_title=False,
        )

    st.divider()
    footer_cols = st.columns([1, 1], gap="large", vertical_alignment="center")
    with footer_cols[1]:
        if st.button(
            "Cancel",
            key=f"scenario_add_operation_cancel_dialog_{dialog_nonce}",
            use_container_width=True,
        ):
            close_add_step_operation_dialog_fn()
            st.rerun()


def render_import_step_operation_dialog(
    draft: dict,
    operation_catalog: list[dict],
    operation_labels_by_id: dict[str, str],
    close_add_step_operation_dialog_fn,
):
    render_add_step_operation_dialog(
        draft,
        operation_catalog,
        operation_labels_by_id,
        close_add_step_operation_dialog_fn,
    )


def render_add_new_step_operation_dialog(draft: dict, close_add_step_operation_dialog_fn):
    render_add_step_operation_dialog(
        draft,
        [],
        {},
        close_add_step_operation_dialog_fn,
    )
