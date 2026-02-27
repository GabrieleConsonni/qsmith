import json
from decimal import Decimal
from uuid import uuid4

import streamlit as st

from scenarios.services.data_loader_service import (
    load_step_editor_context,
    load_step_editor_queues_for_broker,
    load_steps_catalog,
)
from scenarios.services.scenario_api_service import create_step
from scenarios.services.state_keys import (
    ADD_SCENARIO_STEP_DIALOG_NONCE_KEY,
    SCENARIO_FEEDBACK_KEY,
    STEP_EDITOR_BROKERS_KEY,
    STEP_EDITOR_DATABASE_DATASOURCES_KEY,
    STEP_EDITOR_JSON_ARRAYS_KEY,
)

STEP_TYPE_SLEEP = "sleep"
STEP_TYPE_DATA = "data"
STEP_TYPE_DATA_FROM_JSON_ARRAY = "data-from-json-array"
STEP_TYPE_DATA_FROM_DB = "data-from-db"
STEP_TYPE_DATA_FROM_QUEUE = "data-from-queue"
STEP_TYPE_OPTIONS = [
    STEP_TYPE_SLEEP,
    STEP_TYPE_DATA,
    STEP_TYPE_DATA_FROM_JSON_ARRAY,
    STEP_TYPE_DATA_FROM_DB,
    STEP_TYPE_DATA_FROM_QUEUE,
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


def _json_array_catalog_label(json_array_item: dict) -> str:
    return str(json_array_item.get("description") or json_array_item.get("code") or "-")


def _database_datasource_label(datasource_item: dict) -> str:
    return str(datasource_item.get("description") or datasource_item.get("code") or "-")


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


def _step_type_label(step_type: str) -> str:
    labels = {
        STEP_TYPE_SLEEP: "sleep",
        STEP_TYPE_DATA: "data",
        STEP_TYPE_DATA_FROM_JSON_ARRAY: "data-from-json-array",
        STEP_TYPE_DATA_FROM_DB: "data-from-db",
        STEP_TYPE_DATA_FROM_QUEUE: "data-from-queue",
    }
    return labels.get(step_type, step_type or "-")


def _pretty_json(value: object) -> str:
    return json.dumps(value, indent=2, ensure_ascii=True)


def _parse_json_list(value: str) -> tuple[list[dict] | None, str | None]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        return None, f"JSON non valido: {str(exc)}"
    if not isinstance(parsed, list):
        return None, "Il valore deve essere un array JSON."
    return parsed, None


def _new_draft_step(
    default_step_id: str = "",
    order: int = 1,
    edit_mode: bool = True,
) -> dict:
    return {
        "id": None,
        "order": order,
        "step_id": default_step_id,
        "on_failure": "ABORT",
        "operations": [],
        "_ui_key": _new_ui_key(),
        "_edit_mode": edit_mode,
    }


def render_step_component(
    draft: dict,
    scenario_step: dict,
    step_idx: int,
    nonce: int,
    step_catalog: list[dict],
    operation_catalog: list[dict],
    step_labels_by_id: dict[str, str],
    operation_labels_by_id: dict[str, str],
    on_failure_options: list[str],
    render_operation_component_fn,
    open_add_new_step_operation_dialog_fn,
    open_import_step_operation_dialog_fn,
):
    step_ui_key = scenario_step.get("_ui_key") or f"step_{step_idx}"
    scenario_step["_ui_key"] = step_ui_key
    step_edit_mode = bool(scenario_step.get("_edit_mode", False))
    step_order = _safe_int(scenario_step.get("order"), step_idx + 1)
    step_id = str(scenario_step.get("step_id") or "")
    step_label = step_labels_by_id.get(step_id, f"Unknown ({step_id})")

    step_header_cols = st.columns([8, 1, 1], gap="small", vertical_alignment="top")
    with step_header_cols[0]:
        with st.expander(f"Step #{step_order} - {step_label}", expanded=False):
            if step_edit_mode:
                scenario_step["order"] = int(
                    st.number_input(
                        "Step order",
                        min_value=0,
                        value=step_order,
                        key=f"scenario_{nonce}_step_order_{step_ui_key}",
                    )
                )
                if step_catalog:
                    step_options = [str(item.get("id")) for item in step_catalog if item.get("id")]
                    if step_options:
                        current_step_id = str(scenario_step.get("step_id") or "")
                        if current_step_id and current_step_id not in step_options:
                            step_options.insert(0, current_step_id)
                        selected_step_id = st.selectbox(
                            "Step",
                            options=step_options,
                            index=(
                                step_options.index(current_step_id)
                                if current_step_id in step_options
                                else 0
                            ),
                            format_func=lambda _id: step_labels_by_id.get(_id, f"Unknown ({_id})"),
                            key=f"scenario_{nonce}_step_select_{step_ui_key}",
                        )
                        scenario_step["step_id"] = str(selected_step_id)
                    else:
                        scenario_step["step_id"] = st.text_input(
                            "Step id",
                            value=str(scenario_step.get("step_id") or ""),
                            key=f"scenario_{nonce}_step_input_{step_ui_key}",
                        ).strip()
                else:
                    scenario_step["step_id"] = st.text_input(
                        "Step id",
                        value=str(scenario_step.get("step_id") or ""),
                        key=f"scenario_{nonce}_step_input_{step_ui_key}",
                    ).strip()

                on_failure = str(scenario_step.get("on_failure") or "ABORT")
                scenario_step["on_failure"] = st.selectbox(
                    "On failure",
                    options=on_failure_options,
                    index=(
                        on_failure_options.index(on_failure)
                        if on_failure in on_failure_options
                        else 0
                    ),
                    key=f"scenario_{nonce}_step_on_failure_{step_ui_key}",
                )
            else:
                st.caption(f"on_failure: {scenario_step.get('on_failure') or 'ABORT'}")

            st.markdown("**Step operations**")
            operations = scenario_step.get("operations") or []

            for op_idx, operation in enumerate(operations):
                render_operation_component_fn(
                    scenario_step,
                    operation,
                    op_idx,
                    step_ui_key,
                    nonce,
                    operation_catalog,
                    operation_labels_by_id,
                )

            add_operation_cols = st.columns(2, gap="small")
            with add_operation_cols[0]:
                if st.button(
                    "Add new operation",
                    key=f"scenario_{nonce}_step_add_new_operation_{step_ui_key}",
                    icon=":material/add:",
                    use_container_width=True,
                ):
                    open_add_new_step_operation_dialog_fn(step_ui_key)
                    st.rerun()
            with add_operation_cols[1]:
                if st.button(
                    "Import operation",
                    key=f"scenario_{nonce}_step_import_operation_{step_ui_key}",
                    icon=":material/download:",
                    use_container_width=True,
                ):
                    open_import_step_operation_dialog_fn(step_ui_key)
                    st.rerun()

    with step_header_cols[1]:
        icon = ":material/save:" if step_edit_mode else ":material/edit:"
        if st.button(
            "",
            key=f"scenario_{nonce}_step_edit_toggle_{step_ui_key}",
            icon=icon,
            help="Save step" if step_edit_mode else "Modify step",
            use_container_width=True,
        ):
            scenario_step["_edit_mode"] = not step_edit_mode
            st.rerun()
    with step_header_cols[2]:
        if st.button(
            "",
            key=f"scenario_{nonce}_step_delete_{step_ui_key}",
            icon=":material/delete:",
            help="Delete scenario step",
            use_container_width=True,
        ):
            draft.get("steps", []).pop(step_idx)
            st.rerun()


def append_step_to_draft(draft: dict, step_id: str):
    step_id_value = str(step_id or "").strip()
    if not step_id_value:
        return
    steps = draft.setdefault("steps", [])
    steps.append(
        _new_draft_step(
            default_step_id=step_id_value,
            order=len(steps) + 1,
            edit_mode=False,
        )
    )


def build_step_creation_payload(dialog_nonce: int) -> tuple[dict | None, str | None]:
    code = str(st.session_state.get(f"scenario_add_step_code_{dialog_nonce}") or "").strip()
    description = str(
        st.session_state.get(f"scenario_add_step_description_{dialog_nonce}") or ""
    )
    step_type = str(
        st.session_state.get(f"scenario_add_step_type_{dialog_nonce}") or STEP_TYPE_SLEEP
    )

    if not code:
        return None, "Il campo Code dello step e' obbligatorio."

    cfg: dict
    if step_type == STEP_TYPE_SLEEP:
        duration = _safe_int(
            st.session_state.get(f"scenario_add_step_duration_{dialog_nonce}"), 1
        )
        if duration <= 0:
            return None, "Il campo Duration deve essere maggiore di zero."
        cfg = {"stepType": STEP_TYPE_SLEEP, "duration": duration}
    elif step_type == STEP_TYPE_DATA:
        data_raw = str(
            st.session_state.get(f"scenario_add_step_data_{dialog_nonce}") or "[]"
        )
        data_payload, parse_error = _parse_json_list(data_raw)
        if parse_error:
            return None, parse_error
        cfg = {"stepType": STEP_TYPE_DATA, "data": data_payload or []}
    elif step_type == STEP_TYPE_DATA_FROM_JSON_ARRAY:
        json_array_id = str(
            st.session_state.get(f"scenario_add_step_json_array_id_{dialog_nonce}") or ""
        ).strip()
        if not json_array_id:
            return None, "Il campo Json array id e' obbligatorio."
        cfg = {
            "stepType": STEP_TYPE_DATA_FROM_JSON_ARRAY,
            "json_array_id": json_array_id,
        }
    elif step_type == STEP_TYPE_DATA_FROM_DB:
        selected_datasource_id = str(
            st.session_state.get(f"scenario_add_step_db_datasource_id_{dialog_nonce}") or ""
        ).strip()
        if not selected_datasource_id:
            return None, "Il campo Dataset e' obbligatorio."
        cfg = {
            "stepType": STEP_TYPE_DATA_FROM_DB,
            "data_source_id": selected_datasource_id,
        }
    elif step_type == STEP_TYPE_DATA_FROM_QUEUE:
        broker_id = str(
            st.session_state.get(f"scenario_add_step_broker_id_{dialog_nonce}") or ""
        ).strip()
        queue_id = str(
            st.session_state.get(f"scenario_add_step_queue_id_{dialog_nonce}") or ""
        ).strip()
        retry = _safe_int(st.session_state.get(f"scenario_add_step_retry_{dialog_nonce}"), 3)
        wait_time_seconds = _safe_int(
            st.session_state.get(f"scenario_add_step_wait_time_{dialog_nonce}"), 20
        )
        max_messages = _safe_int(
            st.session_state.get(f"scenario_add_step_max_messages_{dialog_nonce}"), 1000
        )
        if not broker_id:
            return None, "Il campo Broker e' obbligatorio."
        if not queue_id:
            return None, "Il campo Queue id e' obbligatorio."
        if retry < 0:
            return None, "Il campo Retry non puo' essere negativo."
        if wait_time_seconds < 0:
            return None, "Il campo Wait time seconds non puo' essere negativo."
        if max_messages <= 0:
            return None, "Il campo Max messages deve essere maggiore di zero."
        cfg = {
            "stepType": STEP_TYPE_DATA_FROM_QUEUE,
            "queue_id": queue_id,
            "retry": retry,
            "wait_time_seconds": wait_time_seconds,
            "max_messages": max_messages,
        }
    else:
        return None, f"Step type non supportato: {step_type}"

    return {
        "code": code,
        "description": description,
        "cfg": cfg,
    }, None


def render_readonly_step_preview(selected_step: dict, dialog_nonce: int):
    if not isinstance(selected_step, dict):
        st.info("Seleziona uno step esistente.")
        return

    step_id = str(selected_step.get("id") or "")
    st.text_input(
        "Code",
        value=str(selected_step.get("code") or ""),
        key=f"scenario_add_step_preview_code_{dialog_nonce}_{step_id}",
        disabled=True,
    )
    st.text_input(
        "Description",
        value=str(selected_step.get("description") or ""),
        key=f"scenario_add_step_preview_description_{dialog_nonce}_{step_id}",
        disabled=True,
    )
    st.text_input(
        "Step type",
        value=_step_type_label(str(selected_step.get("step_type") or "")),
        key=f"scenario_add_step_preview_type_{dialog_nonce}_{step_id}",
        disabled=True,
    )
    st.text_area(
        "Configuration",
        value=_pretty_json(selected_step.get("configuration_json") or {}),
        key=f"scenario_add_step_preview_cfg_{dialog_nonce}_{step_id}",
        disabled=True,
        height=220,
    )


def render_import_scenario_step_dialog(
    draft: dict,
    step_catalog: list[dict],
    step_labels_by_id: dict[str, str],
    close_add_scenario_step_dialog_fn,
):
    dialog_nonce = int(st.session_state.get(ADD_SCENARIO_STEP_DIALOG_NONCE_KEY, 0))
    step_ids = [str(item.get("id")) for item in step_catalog if item.get("id")]
    step_by_id = {str(item.get("id")): item for item in step_catalog if item.get("id")}

    selected_step_id = ""
    if step_ids:
        selected_step_id = st.selectbox(
            "Existing step",
            options=step_ids,
            format_func=lambda _id: step_labels_by_id.get(_id, f"Unknown ({_id})"),
            key=f"scenario_add_step_existing_select_{dialog_nonce}",
        )
    else:
        st.info("Nessuno step disponibile da importare.")

    render_readonly_step_preview(step_by_id.get(selected_step_id), dialog_nonce)
    action_cols = st.columns([7, 2, 2], gap="small")
    with action_cols[1]:
        if st.button(
            "Add",
            key=f"scenario_add_step_add_existing_{dialog_nonce}",
            icon=":material/add:",
            type="secondary",
            use_container_width=True,
            disabled=not bool(selected_step_id),
        ):
            append_step_to_draft(draft, selected_step_id)
            close_add_scenario_step_dialog_fn()
            st.session_state[SCENARIO_FEEDBACK_KEY] = "Scenario step aggiunto."
            st.rerun()
    with action_cols[2]:
        if st.button(
            "Cancel",
            key=f"scenario_add_step_cancel_existing_{dialog_nonce}",
            use_container_width=True,
        ):
            close_add_scenario_step_dialog_fn()
            st.rerun()


def render_add_new_scenario_step_dialog(draft: dict, close_add_scenario_step_dialog_fn):
    dialog_nonce = int(st.session_state.get(ADD_SCENARIO_STEP_DIALOG_NONCE_KEY, 0))
    load_step_editor_context(force=False)
    json_arrays = st.session_state.get(STEP_EDITOR_JSON_ARRAYS_KEY, [])
    database_datasources = st.session_state.get(STEP_EDITOR_DATABASE_DATASOURCES_KEY, [])
    brokers = st.session_state.get(STEP_EDITOR_BROKERS_KEY, [])
    if not isinstance(json_arrays, list):
        json_arrays = []
    if not isinstance(database_datasources, list):
        database_datasources = []
    if not isinstance(brokers, list):
        brokers = []

    json_array_ids = [str(item.get("id")) for item in json_arrays if item.get("id")]
    json_array_by_id = {
        str(item.get("id")): item for item in json_arrays if item.get("id")
    }
    database_datasource_ids = [
        str(item.get("id")) for item in database_datasources if item.get("id")
    ]
    database_datasource_by_id = {
        str(item.get("id")): item for item in database_datasources if item.get("id")
    }
    broker_ids = [str(item.get("id")) for item in brokers if item.get("id")]
    broker_by_id = {str(item.get("id")): item for item in brokers if item.get("id")}

    st.markdown("**New step**")
    st.text_input(
        "Code",
        key=f"scenario_add_step_code_{dialog_nonce}",
    )
    st.text_input(
        "Description",
        key=f"scenario_add_step_description_{dialog_nonce}",
    )
    step_type = st.selectbox(
        "Step type",
        options=STEP_TYPE_OPTIONS,
        format_func=_step_type_label,
        key=f"scenario_add_step_type_{dialog_nonce}",
    )

    if step_type == STEP_TYPE_SLEEP:
        st.number_input(
            "Duration",
            min_value=1,
            value=1,
            step=1,
            key=f"scenario_add_step_duration_{dialog_nonce}",
        )
    elif step_type == STEP_TYPE_DATA:
        data_key = f"scenario_add_step_data_{dialog_nonce}"
        if data_key not in st.session_state:
            st.session_state[data_key] = "[]"
        st.text_area(
            "Data",
            key=data_key,
            height=220,
        )
        if st.button(
            "Beautify",
            key=f"scenario_add_step_data_beautify_{dialog_nonce}",
            icon=":material/auto_fix_high:",
            type="secondary",
            use_container_width=True,
        ):
            data_payload, parse_error = _parse_json_list(
                str(st.session_state.get(data_key) or "[]")
            )
            if parse_error:
                st.error(parse_error)
            else:
                st.session_state[data_key] = _pretty_json(data_payload or [])
    elif step_type == STEP_TYPE_DATA_FROM_JSON_ARRAY:
        json_array_select_key = f"scenario_add_step_json_array_id_{dialog_nonce}"
        _normalize_select_key(json_array_select_key, json_array_ids or [""])
        selected_json_array_id = st.selectbox(
            "Json array",
            options=json_array_ids or [""],
            format_func=lambda _id: (
                _json_array_catalog_label(json_array_by_id.get(_id, {}))
                if _id
                else "Nessun json-array disponibile"
            ),
            key=json_array_select_key,
            disabled=not bool(json_array_ids),
        )
        if not json_array_ids:
            st.info("Nessun json-array configurato.")
        else:
            selected_json_array = json_array_by_id.get(selected_json_array_id, {})
            st.markdown("**Preview json-array**")
            st.json(selected_json_array.get("payload") or [], expanded=True)
    elif step_type == STEP_TYPE_DATA_FROM_DB:
        datasource_select_key = f"scenario_add_step_db_datasource_id_{dialog_nonce}"
        _normalize_select_key(datasource_select_key, database_datasource_ids or [""])
        st.selectbox(
            "Dataset",
            options=database_datasource_ids or [""],
            format_func=lambda _id: (
                _database_datasource_label(database_datasource_by_id.get(_id, {}))
                if _id
                else "Nessun dataset disponibile"
            ),
            key=datasource_select_key,
            disabled=not bool(database_datasource_ids),
        )
        if not database_datasource_ids:
            st.info("Nessun dataset database configurato.")
    elif step_type == STEP_TYPE_DATA_FROM_QUEUE:
        broker_select_key = f"scenario_add_step_broker_id_{dialog_nonce}"
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
        queue_select_key = f"scenario_add_step_queue_id_{dialog_nonce}"
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
        st.number_input(
            "Retry",
            min_value=0,
            value=3,
            step=1,
            key=f"scenario_add_step_retry_{dialog_nonce}",
        )
        st.number_input(
            "Wait time seconds",
            min_value=0,
            value=20,
            step=1,
            key=f"scenario_add_step_wait_time_{dialog_nonce}",
        )
        st.number_input(
            "Max messages",
            min_value=1,
            value=1000,
            step=1,
            key=f"scenario_add_step_max_messages_{dialog_nonce}",
        )

    create_cols = st.columns([6, 3, 3], gap="small")
    with create_cols[1]:
        if st.button(
            "Save and add",
            key=f"scenario_add_step_save_and_add_{dialog_nonce}",
            icon=":material/save:",
            type="secondary",
            use_container_width=True,
        ):
            payload, validation_error = build_step_creation_payload(dialog_nonce)
            if validation_error:
                st.error(validation_error)
                return

            try:
                response = create_step(payload or {})
            except Exception as exc:
                st.error(f"Errore creazione step: {str(exc)}")
                return

            created_step_id = str(response.get("id") or "").strip()
            if not created_step_id:
                st.error("Risposta creazione step non valida.")
                return

            load_steps_catalog(force=True)
            append_step_to_draft(draft, created_step_id)
            close_add_scenario_step_dialog_fn()
            st.session_state[SCENARIO_FEEDBACK_KEY] = "Nuovo step creato e aggiunto."
            st.rerun()
    with create_cols[2]:
        if st.button(
            "Cancel",
            key=f"scenario_add_step_cancel_new_{dialog_nonce}",
            use_container_width=True,
        ):
            close_add_scenario_step_dialog_fn()
            st.rerun()

