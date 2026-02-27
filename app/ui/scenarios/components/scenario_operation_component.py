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
from scenarios.services.scenario_api_service import create_operation
from scenarios.services.state_keys import (
    ADD_STEP_OPERATION_DIALOG_NONCE_KEY,
    ADD_STEP_OPERATION_DIALOG_TARGET_STEP_UI_KEY,
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
    default_operation_id: str = "",
    order: int = 1,
) -> dict:
    return {
        "id": None,
        "order": order,
        "operation_id": default_operation_id,
        "_ui_key": _new_ui_key(),
    }


def _resolve_operation_description(
    operation_id: str,
    operation_catalog: list[dict],
    operation_labels_by_id: dict[str, str],
) -> str:
    operation_item = next(
        (
            item
            for item in operation_catalog
            if str(item.get("id") or "") == str(operation_id or "")
        ),
        None,
    )
    if isinstance(operation_item, dict):
        return str(
            operation_item.get("description")
            or operation_item.get("code")
            or operation_labels_by_id.get(str(operation_id or ""), "")
            or f"Unknown ({operation_id})"
        )
    return operation_labels_by_id.get(str(operation_id or ""), f"Unknown ({operation_id})")


@st.dialog("Modify operation", width="large")
def _edit_step_operation_dialog(
    scenario_step: dict,
    operation: dict,
    op_idx: int,
    step_ui_key: str,
    nonce: int,
    operation_catalog: list[dict],
    operation_labels_by_id: dict[str, str],
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
            st.rerun()
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
            st.rerun()
    with action_cols[3]:
        if st.button(
            "Cancel",
            key=f"scenario_{nonce}_step_{step_ui_key}_operation_edit_cancel_{operation_ui_key}",
            use_container_width=True,
        ):
            st.rerun()

def _operation_type_label(operation_type: str) -> str:
    normalized_type = str(operation_type or "").strip().replace("_", "-").lower()
    if not normalized_type:
        return "-"
    label = normalized_type.replace("-", " ")
    return f"{label}" if label else "-"

def render_operation_component(
    scenario_step: dict,
    operation: dict,
    op_idx: int,
    step_ui_key: str,
    nonce: int,
    operation_catalog: list[dict],
    operation_labels_by_id: dict[str, str],
):
    operation_ui_key = operation.get("_ui_key") or f"{step_ui_key}_op_{op_idx}"
    operation["_ui_key"] = operation_ui_key
    operation_id = str(operation.get("operation_id") or "").strip()
    selected_operation = next(
        (
            item
            for item in operation_catalog
            if str(item.get("id") or "").strip() == operation_id
        ),
        None,
    )
    
    operation_description = _resolve_operation_description(
        operation_id,
        operation_catalog,
        operation_labels_by_id,
    )

    operation_type = _operation_type_label(str(selected_operation.get("operation_type") or "") if isinstance(selected_operation, dict) else "")
    
    operation_action_cols = st.columns([1, 20, 1], gap="small", vertical_alignment="center")
    with operation_action_cols[1]:
        with st.container(border=True):
            st.markdown(f"**{operation_description}**")
            st.markdown(f"*{operation_type} operation*")
            _render_operation_details(selected_operation)
    with operation_action_cols[2]:
        if st.button(
            "",
            key=f"scenario_{nonce}_step_{step_ui_key}_operation_more_actions_{operation_ui_key}",
            icon=":material/more_vert:",
            help="Modify operation",
            use_container_width=True,
            type="tertiary",
        ):
            _edit_step_operation_dialog(
                scenario_step=scenario_step,
                operation=operation,
                op_idx=op_idx,
                step_ui_key=step_ui_key,
                nonce=nonce,
                operation_catalog=operation_catalog,
                operation_labels_by_id=operation_labels_by_id,
            )


def find_draft_step_by_ui_key(draft: dict, step_ui_key: str) -> dict | None:
    if not step_ui_key:
        return None
    for scenario_step in draft.get("steps") or []:
        if str(scenario_step.get("_ui_key") or "") == str(step_ui_key):
            return scenario_step
    return None


def append_operation_to_step(scenario_step: dict, operation_id: str):
    operation_id_value = str(operation_id or "").strip()
    if not operation_id_value:
        return
    operations = scenario_step.setdefault("operations", [])
    operations.append(
        _new_draft_operation(
            default_operation_id=operation_id_value,
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


def render_import_step_operation_dialog(
    draft: dict,
    operation_catalog: list[dict],
    operation_labels_by_id: dict[str, str],
    close_add_step_operation_dialog_fn,
):
    dialog_nonce = int(st.session_state.get(ADD_STEP_OPERATION_DIALOG_NONCE_KEY, 0))
    scenario_step = _resolve_target_step_for_operation_dialog(
        draft,
        dialog_nonce,
        close_add_step_operation_dialog_fn,
    )
    if not isinstance(scenario_step, dict):
        return

    operation_ids = [str(item.get("id")) for item in operation_catalog if item.get("id")]
    operation_by_id = {
        str(item.get("id")): item for item in operation_catalog if item.get("id")
    }

    selected_operation_id = ""
    if operation_ids:
        selected_operation_id = st.selectbox(
            "Existing operation",
            options=operation_ids,
            format_func=lambda _id: operation_labels_by_id.get(_id, f"Unknown ({_id})"),
            key=f"scenario_add_operation_existing_select_{dialog_nonce}",
        )
    else:
        st.info("Nessuna operation disponibile da importare.")

    render_readonly_operation_preview(operation_by_id.get(selected_operation_id), dialog_nonce)
    action_cols = st.columns([7, 2, 2], gap="small")
    with action_cols[1]:
        if st.button(
            "Add",
            key=f"scenario_add_operation_add_existing_{dialog_nonce}",
            icon=":material/add:",
            type="secondary",
            use_container_width=True,
            disabled=not bool(selected_operation_id),
        ):
            append_operation_to_step(scenario_step, selected_operation_id)
            close_add_step_operation_dialog_fn()
            st.session_state[SCENARIO_FEEDBACK_KEY] = "Operazione aggiunta."
            st.rerun()
    with action_cols[2]:
        if st.button(
            "Cancel",
            key=f"scenario_add_operation_cancel_existing_{dialog_nonce}",
            use_container_width=True,
        ):
            close_add_step_operation_dialog_fn()
            st.rerun()


def render_add_new_step_operation_dialog(draft: dict, close_add_step_operation_dialog_fn):
    dialog_nonce = int(st.session_state.get(ADD_STEP_OPERATION_DIALOG_NONCE_KEY, 0))
    scenario_step = _resolve_target_step_for_operation_dialog(
        draft,
        dialog_nonce,
        close_add_step_operation_dialog_fn,
    )
    if not isinstance(scenario_step, dict):
        return

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

    st.markdown("**New operation**")
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

    create_cols = st.columns([6, 3, 3], gap="small")
    with create_cols[1]:
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
            append_operation_to_step(scenario_step, created_operation_id)
            close_add_step_operation_dialog_fn()
            st.session_state[SCENARIO_FEEDBACK_KEY] = "Nuova operazione creata e aggiunta."
            st.rerun()
    with create_cols[2]:
        if st.button(
            "Cancel",
            key=f"scenario_add_operation_cancel_new_{dialog_nonce}",
            use_container_width=True,
        ):
            close_add_step_operation_dialog_fn()
            st.rerun()
