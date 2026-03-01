import json
from decimal import Decimal
from uuid import uuid4

import streamlit as st

from database_datasources.services.data_loader_service import (
    load_database_datasource_preview,
)
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
    STEP_EDITOR_QUEUES_BY_BROKER_KEY,
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
STEP_STATUS_SUCCESS = "success"
STEP_STATUS_ERROR = "error"
STEP_STATUS_RUNNING = "running"
STEP_STATUS_IDLE = "idle"


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
    normalized_type = str(step_type or "").strip().replace("_", "-").lower()
    if not normalized_type:
        return "-"
    label = normalized_type.replace("-", " ")
    return f"Read {label}" if label else "-"


def _step_status_icon(step_status: str) -> str:
    normalized_status = str(step_status or "").strip().lower()
    if normalized_status == STEP_STATUS_SUCCESS:
        return ":material/check_circle:"
    if normalized_status == STEP_STATUS_ERROR:
        return ":material/error:"
    if normalized_status == STEP_STATUS_RUNNING:
        return ":material/pending:"
    return ":material/radio_button_unchecked:"


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


def _normalize_object_name(value: object) -> str:
    return str(value or "").strip().lower()


def _split_schema_and_object(table_name: str) -> tuple[str, str]:
    normalized = str(table_name or "").strip()
    if "." not in normalized:
        return "", normalized
    schema, object_name = normalized.split(".", 1)
    return schema.strip(), object_name.strip()


def _find_dataset_from_configuration(
    configuration_json: dict,
    database_datasources: list[dict],
    database_datasource_by_id: dict[str, dict],
) -> tuple[str, dict]:
    configured_dataset_id = str(
        _resolve_configuration_value(
            configuration_json,
            "data_source_id",
            "dataset_id",
            "dataSourceId",
            "datasetId",
        )
        or ""
    ).strip()
    if configured_dataset_id:
        by_id = database_datasource_by_id.get(configured_dataset_id, {})
        if by_id:
            return configured_dataset_id, by_id
        by_code = next(
            (
                item
                for item in database_datasources
                if str(item.get("code") or "").strip() == configured_dataset_id
            ),
            {},
        )
        if by_code:
            return str(by_code.get("id") or configured_dataset_id), by_code

    legacy_connection_id = str(
        _resolve_configuration_value(configuration_json, "connection_id", "connectionId") or ""
    ).strip()
    legacy_table_name = str(
        _resolve_configuration_value(configuration_json, "table_name", "tableName") or ""
    ).strip()
    legacy_object_name = str(
        _resolve_configuration_value(configuration_json, "object_name", "objectName") or ""
    ).strip()
    legacy_schema = str(
        _resolve_configuration_value(configuration_json, "schema", "db_schema") or ""
    ).strip()

    if not legacy_connection_id and not legacy_table_name and not legacy_object_name:
        return configured_dataset_id, {}

    derived_schema, derived_object_name = _split_schema_and_object(legacy_table_name)
    expected_schema = _normalize_object_name(legacy_schema or derived_schema)
    expected_object_name = _normalize_object_name(legacy_object_name or derived_object_name)

    for datasource_item in database_datasources:
        payload = _safe_dict(datasource_item.get("payload") or {})
        item_connection_id = str(payload.get("connection_id") or "").strip()
        item_schema = _normalize_object_name(payload.get("schema"))
        item_object_name = _normalize_object_name(payload.get("object_name"))
        if legacy_connection_id and item_connection_id != legacy_connection_id:
            continue
        if expected_schema and item_schema and item_schema != expected_schema:
            continue
        if expected_object_name and item_object_name != expected_object_name:
            continue
        return str(datasource_item.get("id") or ""), datasource_item

    return configured_dataset_id, {}


def _resolve_configuration_value(configuration_json: dict, *keys: str):
    for key in keys:
        value = configuration_json.get(key)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _render_step_details_sleep(step_type: str, configuration_json: dict, step_status: str):
    duration = _safe_int(configuration_json.get("duration"), 0)
    st.markdown(
        f"**Step type: {_step_type_label(step_type)}**"
    )
    st.write(f"Duration: {duration} sec")
        

def _render_step_details_data(
    step_type: str,
    configuration_json: dict,
    step_ui_key: str,
    step_status: str,
):
    data_payload = configuration_json.get("data")
    st.markdown(
        f"**Step type: {_step_type_label(step_type)}**"
    )
    st.json(data_payload if data_payload is not None else {}, expanded=False)


def _render_step_details_data_from_json_array(
    step_type: str,
    configuration_json: dict,
    json_arrays_by_id: dict[str, dict],
    step_status: str,
):
    json_array_id = str(
        _resolve_configuration_value(configuration_json, "json_array_id", "jsonArrayId") or ""
    ).strip()
    selected_json_array = json_arrays_by_id.get(json_array_id, {})
    st.markdown(
        f"**Step type: {_step_type_label(step_type)}**"
    )
    
    code = str(selected_json_array.get("code") or "")
    descritption = str(selected_json_array.get("description") or "")
    st.write(f"Json Array : {code} - {descritption}" if code or descritption else "-" )

    st.json(selected_json_array.get("payload") or {}, expanded=False)
        

def _render_step_details_data_from_db(
    step_type: str,
    configuration_json: dict,
    step_ui_key: str,
    database_datasources: list[dict],
    database_datasource_by_id: dict[str, dict],
    step_status: str,
):
    dataset_id, selected_dataset = _find_dataset_from_configuration(
        configuration_json,
        database_datasources,
        database_datasource_by_id,
    )
    st.markdown(
        f"**Step type: {_step_type_label(step_type)}**"
    )
    code = str(selected_dataset.get("code") or "").strip()
    description = str(selected_dataset.get("description") or "").strip()
    if code or description:
        st.write(f"Dataset: {code} - {description}" if code and description else (code or description))
    elif dataset_id:
        st.write(f"Dataset id: {dataset_id} (not found in catalog)")
    else:
        st.write("Dataset: -")

    if not dataset_id:
        return

    preview_visible_key = f"scenario_step_db_preview_visible_{step_ui_key}"
    is_preview_visible = bool(st.session_state.get(preview_visible_key, False))
    preview_label = "Hide table preview" if is_preview_visible else "Show table preview"
    if st.button(preview_label, key=f"scenario_step_db_preview_btn_{step_ui_key}"):
        is_preview_visible = not is_preview_visible
        st.session_state[preview_visible_key] = is_preview_visible

    if not is_preview_visible:
        return

    preview_payload = load_database_datasource_preview(dataset_id, force=False)
    if not isinstance(preview_payload, dict):
        st.info("No preview available.")
        return
    if preview_payload.get("error"):
        st.error(str(preview_payload.get("error")))
        return

    object_name = str(preview_payload.get("object_name") or "-")
    object_type = str(preview_payload.get("object_type") or "-")
    row_count = _safe_int(preview_payload.get("count"), 0)
    st.caption(f"Preview: {object_type} {object_name} ({row_count} rows)")
    rows = preview_payload.get("rows")
    if isinstance(rows, list) and rows:
        st.dataframe(rows, use_container_width=True)
    else:
        st.info("Nessuna riga disponibile per la preview.")
        


def _find_queue_and_broker(
    queue_id: str,
    broker_id: str,
    brokers_by_id: dict[str, dict],
) -> tuple[dict, dict]:
    queue_id_value = str(queue_id or "").strip()
    broker_id_value = str(broker_id or "").strip()
    if not queue_id_value:
        return {}, brokers_by_id.get(broker_id_value, {}) if broker_id_value else {}

    def _find_queue_in_items(items: list[dict], target_queue_id: str) -> dict:
        return next(
            (
                item
                for item in items
                if str(item.get("id") or "").strip() == target_queue_id
            ),
            {},
        )

    if broker_id_value:
        queues = load_step_editor_queues_for_broker(broker_id_value, force=False)
        queue_item = _find_queue_in_items(queues, queue_id_value)
        return queue_item, brokers_by_id.get(broker_id_value, {})

    queues_by_broker = st.session_state.get(STEP_EDITOR_QUEUES_BY_BROKER_KEY, {})
    if isinstance(queues_by_broker, dict):
        for cached_broker_id, queues in queues_by_broker.items():
            queue_item = _find_queue_in_items(_safe_list(queues), queue_id_value)
            if queue_item:
                broker_item = brokers_by_id.get(str(cached_broker_id), {})
                return queue_item, broker_item

    for current_broker_id, broker_item in brokers_by_id.items():
        queues = load_step_editor_queues_for_broker(str(current_broker_id), force=False)
        queue_item = _find_queue_in_items(queues, queue_id_value)
        if queue_item:
            return queue_item, broker_item

    return {}, {}


def _render_step_details_data_from_queue(
    step_type: str,
    configuration_json: dict,
    brokers_by_id: dict[str, dict],
    step_status: str,
):
    broker_id = str(
        _resolve_configuration_value(configuration_json, "broker_id", "brokerId") or ""
    ).strip()
    queue_id = str(
        _resolve_configuration_value(configuration_json, "queue_id", "queueId") or ""
    ).strip()
    queue_item, broker_item = _find_queue_and_broker(queue_id, broker_id, brokers_by_id)

    st.markdown(
        f"**Step type: {_step_type_label(step_type)}**"
    )

    broker_description = str(broker_item.get("description") or "").strip()
    queue_description = str(queue_item.get("description") or "").strip()
    st.write(f"{queue_description} [{broker_description}]" if broker_description and queue_description else (f"Queue: {queue_description}" if queue_description else (f"Broker: {broker_description}" if broker_description else "Queue and Broker: -")))



def _render_step_details_unknown(step_type: str, configuration_json: dict, step_status: str):
    with st.container(border=True):
        st.markdown(
            f"**Step type: {_step_type_label(step_type)}**"
        )
        st.code(_pretty_json(configuration_json), language="json")


def _render_step_details_component(selected_step: dict, step_ui_key: str, step_status: str):
    if not isinstance(selected_step, dict):
        st.caption("Step type: -")
        st.info("Step non trovato nel catalogo.")    
        return

    load_step_editor_context(force=False)

    step_type = str(selected_step.get("step_type") or "").strip()
    configuration_json = _safe_dict(selected_step.get("configuration_json") or {})
    resolved_step_type = str(
        _resolve_configuration_value(configuration_json, "stepType", "step_type")
        or step_type
    )
    normalized_step_type = str(resolved_step_type or "").strip().replace("_", "-").lower()

    json_arrays = _safe_list(st.session_state.get(STEP_EDITOR_JSON_ARRAYS_KEY, []))
    database_datasources = _safe_list(st.session_state.get(STEP_EDITOR_DATABASE_DATASOURCES_KEY, []))
    brokers = _safe_list(st.session_state.get(STEP_EDITOR_BROKERS_KEY, []))

    json_arrays_by_id = _map_by_id(json_arrays)
    database_datasource_by_id = _map_by_id(database_datasources)
    brokers_by_id = _map_by_id(brokers)

    if normalized_step_type == STEP_TYPE_SLEEP:
        _render_step_details_sleep(resolved_step_type, configuration_json, step_status)
        return
    if normalized_step_type == STEP_TYPE_DATA:
        _render_step_details_data(
            resolved_step_type,
            configuration_json,
            step_ui_key,
            step_status,
        )
        return
    if normalized_step_type == STEP_TYPE_DATA_FROM_JSON_ARRAY:
        _render_step_details_data_from_json_array(
            resolved_step_type,
            configuration_json,
            json_arrays_by_id,
            step_status,
        )
        return
    if normalized_step_type == STEP_TYPE_DATA_FROM_DB:
        _render_step_details_data_from_db(
            resolved_step_type,
            configuration_json,
            step_ui_key,
            database_datasources,
            database_datasource_by_id,
            step_status,
        )
        return
    if normalized_step_type == STEP_TYPE_DATA_FROM_QUEUE:
        _render_step_details_data_from_queue(
            resolved_step_type,
            configuration_json,
            brokers_by_id,
            step_status,
        )
        return

    _render_step_details_unknown(resolved_step_type, configuration_json, step_status)


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


def _reload_draft_steps(draft: dict):
    steps = draft.get("steps")
    if not isinstance(steps, list):
        return
    indexed_steps = list(enumerate(steps))
    indexed_steps.sort(
        key=lambda item: (_safe_int(item[1].get("order"), item[0] + 1), item[0])
    )
    draft["steps"] = [step for _, step in indexed_steps]


@st.dialog("Modify step", width="large")
def _edit_scenario_step_dialog(
    draft: dict,
    scenario_step: dict,
    step_idx: int,
    nonce: int,
    step_catalog: list[dict],
    step_labels_by_id: dict[str, str],
    on_failure_options: list[str],
):
    step_ui_key = scenario_step.get("_ui_key") or f"step_{step_idx}"
    scenario_step["_ui_key"] = step_ui_key

    selected_order = int(
        st.number_input(
            "Step order",
            min_value=0,
            value=_safe_int(scenario_step.get("order"), step_idx + 1),
            key=f"scenario_{nonce}_step_order_{step_ui_key}",
        )
    )

    on_failure_value = str(scenario_step.get("on_failure") or "ABORT")
    if on_failure_value not in on_failure_options:
        on_failure_value = on_failure_options[0] if on_failure_options else "ABORT"
    selected_on_failure = st.selectbox(
        "On failure",
        options=on_failure_options or ["ABORT"],
        index=(on_failure_options.index(on_failure_value) if on_failure_options else 0),
        key=f"scenario_{nonce}_step_on_failure_{step_ui_key}",
    )

    action_cols = st.columns([4, 2, 2, 2], gap="small", vertical_alignment="center")
    with action_cols[1]:
        if st.button(
            "Save",
            key=f"scenario_{nonce}_step_edit_save_{step_ui_key}",
            icon=":material/save:",
            type="secondary",
            use_container_width=True,
        ):
            scenario_step["order"] = selected_order
            scenario_step["on_failure"] = str(selected_on_failure or "ABORT")
            _reload_draft_steps(draft)
            st.rerun()
    with action_cols[2]:
        if st.button(
            "Delete",
            key=f"scenario_{nonce}_step_edit_delete_{step_ui_key}",
            icon=":material/delete:",
            type="secondary",
            use_container_width=True,
        ):
            steps = draft.get("steps", [])
            if 0 <= step_idx < len(steps):
                steps.pop(step_idx)
            st.rerun()
    with action_cols[3]:
        if st.button(
            "Cancel",
            key=f"scenario_{nonce}_step_edit_cancel_{step_ui_key}",
            use_container_width=True,
        ):
            st.rerun()


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
    execute_step_action_fn,
    get_step_status_fn,
    get_operation_status_fn,
):
    step_ui_key = scenario_step.get("_ui_key") or f"step_{step_idx}"
    scenario_step["_ui_key"] = step_ui_key
    step_id = str(scenario_step.get("step_id") or "")
    step_label = step_labels_by_id.get(step_id, f"Unknown ({step_id})")
    selected_step = next(
        (
            item
            for item in step_catalog
            if str(item.get("id") or "").strip() == step_id
        ),
        None,
    )

    step_status = (
        str(get_step_status_fn(scenario_step) or STEP_STATUS_IDLE)
        if callable(get_step_status_fn)
        else STEP_STATUS_IDLE
    )

    step_layout_cols = st.columns([1, 19, 1], vertical_alignment="top")
    with step_layout_cols[0]:
        st.button(
            "",
            key=f"scenario_{nonce}_step_status_{step_ui_key}",
            icon=_step_status_icon(step_status),
            type="tertiary",
            disabled=True,
            use_container_width=True,
        )
    with step_layout_cols[1]:
        with st.expander(f"{step_label}", expanded=False):
            _render_step_details_component(selected_step, step_ui_key, step_status)
            on_failure_value = str(scenario_step.get("on_failure") or "-")
            st.markdown(f"**On failure:** {on_failure_value}")

            st.divider()
            st.write("**Step Operations**")

            operations = scenario_step.get("operations") or []
            for op_idx, operation in enumerate(operations):
                operation_status = (
                    str(get_operation_status_fn(scenario_step, operation) or STEP_STATUS_IDLE)
                    if callable(get_operation_status_fn)
                    else STEP_STATUS_IDLE
                )
                render_operation_component_fn(
                    scenario_step,
                    operation,
                    op_idx,
                    step_ui_key,
                    nonce,
                    operation_catalog,
                    operation_labels_by_id,
                    operation_status=operation_status,
                )

            st.divider()
            add_operation_cols = st.columns([5, 2, 2, 2, 2, 5], gap="small")
            with add_operation_cols[1]:
                if st.button(
                    "",
                    help="Add new operation",
                    key=f"scenario_{nonce}_step_add_new_operation_{step_ui_key}",
                    icon=":material/add:",
                    use_container_width=True,
                    type="tertiary"
                ):
                    open_add_new_step_operation_dialog_fn(step_ui_key)
                    st.rerun()
            with add_operation_cols[2]:
                if st.button(
                    "",
                    help="Import operation",
                    key=f"scenario_{nonce}_step_import_operation_{step_ui_key}",
                    icon=":material/download:",
                    use_container_width=True,
                    type="tertiary"
                ):
                    open_import_step_operation_dialog_fn(step_ui_key)
                    st.rerun()
            with add_operation_cols[3]:
                if st.button(
                    "",
                    help="Esegui solo questo step",
                    key=f"scenario_{nonce}_step_execute_{step_ui_key}",
                    icon=":material/play_arrow:",
                    use_container_width=True,
                    type="tertiary",
                    disabled=not bool(str(scenario_step.get("id") or "").strip()),
                ):
                    if callable(execute_step_action_fn):
                        execute_step_action_fn(scenario_step, False)
            with add_operation_cols[4]:
                if st.button(
                    "",
                    help="Esegui gli step precedenti e quello corrente",
                    key=f"scenario_{nonce}_step_execute_with_previous_{step_ui_key}",
                    icon=":material/playlist_play:",
                    use_container_width=True,
                    type="tertiary",
                    disabled=not bool(str(scenario_step.get("id") or "").strip()),
                ):
                    if callable(execute_step_action_fn):
                        execute_step_action_fn(scenario_step, True)
    with step_layout_cols[2]:
        if st.button(
            "",
            key=f"scenario_{nonce}_step_more_actions_{step_ui_key}",
            icon=":material/more_vert:",
            help="Modify step",
            use_container_width=True,
            type="tertiary"
        ):
            _edit_scenario_step_dialog(
                draft=draft,
                scenario_step=scenario_step,
                step_idx=step_idx,
                nonce=nonce,
                step_catalog=step_catalog,
                step_labels_by_id=step_labels_by_id,
                on_failure_options=on_failure_options,
            )

        


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
            "dataset_id": selected_datasource_id,
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
    
    st.divider()

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
            st.json(selected_json_array.get("payload") or [], expanded=False)
    
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

        col_num_inputs = st.columns(3, gap="small")
        with col_num_inputs[0]:
            st.number_input(
                "Retry",
                min_value=0,
                value=3,
                step=1,
                key=f"scenario_add_step_retry_{dialog_nonce}",
            )
        with col_num_inputs[1]:
            st.number_input(
                "Wait time seconds",
                min_value=0,
                value=20,
                step=1,
                key=f"scenario_add_step_wait_time_{dialog_nonce}",
            )
        with col_num_inputs[2]:
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
