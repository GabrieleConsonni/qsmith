from decimal import Decimal
from datetime import datetime
import time
from uuid import uuid4

import streamlit as st

from scenarios.components.scenario_operation_component import (
    render_add_step_operation_dialog as operation_render_add_dialog,
    render_operation_component as operation_render_component,
)
from steps.step_component import (
    render_add_scenario_step_dialog as step_render_add_dialog,
    render_step_component as step_render_component,
)
from scenarios.services.data_loader_service import (
    load_scenarios,
    load_scenarios_context,
)

from scenarios.services.scenario_api_service import (
    create_scenario,
    delete_scenario_execution_by_id,
    delete_scenario_by_id,
    execute_scenario_by_id,
    execute_scenario_step_by_id,
    get_scenario_by_id,
    get_scenario_executions,
    update_scenario,
)
from scenarios.services.execution_stream_service import (
    get_execution_state,
    register_execution_listener,
)
from scenarios.services.state_keys import (
    ADD_SCENARIO_STEP_DIALOG_NONCE_KEY,
    ADD_SCENARIO_STEP_DIALOG_OPEN_KEY,
    ADD_STEP_OPERATION_DIALOG_NONCE_KEY,
    ADD_STEP_OPERATION_DIALOG_OPEN_KEY,
    ADD_STEP_OPERATION_DIALOG_TARGET_STEP_UI_KEY,
    ON_FAILURE_OPTIONS,
    OPERATIONS_CATALOG_KEY,
    PENDING_SCENARIO_SWITCH_KEY,
    SCENARIOS_KEY,
    SCENARIO_DRAFT_KEY,
    SCENARIO_EDITOR_MODE_KEY,
    SCENARIO_EDITOR_NONCE_KEY,
    SCENARIO_EDITOR_EXECUTIONS_KEY,
    SCENARIO_FEEDBACK_KEY,
    SCENARIO_LAST_EXECUTION_ID_KEY,
    SCENARIO_SELECTED_EXECUTION_ID_KEY,
    SELECTED_SCENARIO_ID_KEY,
    STEPS_CATALOG_KEY,
)

SCENARIOS_LIST_PAGE_PATH = "pages/Scenarios.py"
SCENARIO_EDITOR_PAGE_PATH = "pages/ScenarioEditor.py"
STEP_TYPE_SLEEP = "sleep"


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


def _format_datetime(value) -> str:
    if value is None:
        return "-"
    return str(value).replace("T", " ")


def _parse_datetime(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    raw_value = str(value).strip()
    if not raw_value:
        return None
    normalized = raw_value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        pass
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(raw_value, fmt)
        except ValueError:
            continue
    return None


def _format_datetime_compact(value) -> str:
    parsed = _parse_datetime(value)
    if parsed is None:
        return _format_datetime(value)
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def _format_time_only(value) -> str:
    parsed = _parse_datetime(value)
    if parsed is None:
        return "-"
    return parsed.strftime("%H:%M:%S")


def _execution_status_label(status: str) -> str:
    normalized = str(status or "").strip().lower()
    if normalized == "success":
        return "success"
    if normalized == "error":
        return "error"
    if normalized == "running":
        return "running"
    return normalized or "unknown"


def _execution_status_icon(status: str) -> str:
    normalized_status = _execution_status_label(status)
    if normalized_status == "success":
        return ":material/check_circle:"
    if normalized_status == "error":
        return ":material/error:"
    if normalized_status == "running":
        return ":material/pending:"
    return ":material/radio_button_unchecked:"


def _clear_pending_switch():
    st.session_state.pop(PENDING_SCENARIO_SWITCH_KEY, None)


def _bump_editor_nonce():
    st.session_state[SCENARIO_EDITOR_NONCE_KEY] = (
        int(st.session_state.get(SCENARIO_EDITOR_NONCE_KEY, 0)) + 1
    )


def _set_editor_draft(draft: dict | None, mode: str):
    previous_draft = st.session_state.get(SCENARIO_DRAFT_KEY)
    previous_scenario_id = str((previous_draft or {}).get("id") or "").strip()
    next_scenario_id = str((draft or {}).get("id") or "").strip()
    if previous_scenario_id != next_scenario_id:
        st.session_state.pop(SCENARIO_LAST_EXECUTION_ID_KEY, None)
        st.session_state.pop(SCENARIO_SELECTED_EXECUTION_ID_KEY, None)
        st.session_state.pop(SCENARIO_EDITOR_EXECUTIONS_KEY, None)

    st.session_state[SCENARIO_DRAFT_KEY] = draft
    st.session_state[SCENARIO_EDITOR_MODE_KEY] = mode
    _close_add_scenario_step_dialog()
    _close_add_step_operation_dialog()
    _clear_pending_switch()
    _bump_editor_nonce()


def _resolve_selected_scenario_id(scenarios: list[dict]) -> str | None:
    scenario_ids = [str(item.get("id")) for item in scenarios if item.get("id")]
    selected_id = st.session_state.get(SELECTED_SCENARIO_ID_KEY)
    if not scenario_ids:
        st.session_state[SELECTED_SCENARIO_ID_KEY] = None
        return None
    if not selected_id or str(selected_id) not in scenario_ids:
        st.session_state[SELECTED_SCENARIO_ID_KEY] = scenario_ids[0]
    return str(st.session_state.get(SELECTED_SCENARIO_ID_KEY))


def _step_catalog_label(step_item: dict) -> str:
    code = step_item.get("code") or "-"
    description = step_item.get("description") or "-"
    return f"{code} ({description})"


def _operation_catalog_label(operation_item: dict) -> str:
    code = operation_item.get("code") or "-"
    description = operation_item.get("description") or "-"
    return f"{code} ({description})"


def _open_add_scenario_step_dialog():
    _close_add_step_operation_dialog()
    st.session_state[ADD_SCENARIO_STEP_DIALOG_OPEN_KEY] = True
    st.session_state[ADD_SCENARIO_STEP_DIALOG_NONCE_KEY] = (
        int(st.session_state.get(ADD_SCENARIO_STEP_DIALOG_NONCE_KEY, 0)) + 1
    )


def _close_add_scenario_step_dialog():
    st.session_state[ADD_SCENARIO_STEP_DIALOG_OPEN_KEY] = False


def _open_add_step_operation_dialog(step_ui_key: str):
    if not step_ui_key:
        return
    _close_add_scenario_step_dialog()
    st.session_state[ADD_STEP_OPERATION_DIALOG_OPEN_KEY] = True
    st.session_state[ADD_STEP_OPERATION_DIALOG_TARGET_STEP_UI_KEY] = step_ui_key
    st.session_state[ADD_STEP_OPERATION_DIALOG_NONCE_KEY] = (
        int(st.session_state.get(ADD_STEP_OPERATION_DIALOG_NONCE_KEY, 0)) + 1
    )


def _open_add_new_step_operation_dialog(step_ui_key: str):
    _open_add_step_operation_dialog(step_ui_key)


def _close_add_step_operation_dialog():
    st.session_state[ADD_STEP_OPERATION_DIALOG_OPEN_KEY] = False
    st.session_state.pop(ADD_STEP_OPERATION_DIALOG_TARGET_STEP_UI_KEY, None)


def _new_scenario_draft() -> dict:
    return {
        "id": None,
        "code": "",
        "description": "",
        "steps": [],
    }


def _build_scenario_draft(scenario_id: str) -> dict | None:
    try:
        scenario = get_scenario_by_id(scenario_id)
    except Exception:
        st.error("Errore caricamento dettaglio scenario.")
        return None

    steps_payload = scenario.get("steps") or []
    draft_steps: list[dict] = []
    for step_idx, scenario_step in enumerate(steps_payload):
        operations_payload = scenario_step.get("operations") or []
        draft_operations: list[dict] = []
        for op_idx, step_operation in enumerate(operations_payload):
            operation_cfg = (
                step_operation.get("configuration_json")
                if isinstance(step_operation.get("configuration_json"), dict)
                else {}
            )
            draft_operations.append(
                {
                    "id": step_operation.get("id"),
                    "order": _safe_int(step_operation.get("order"), op_idx + 1),
                    "code": str(step_operation.get("code") or ""),
                    "description": str(step_operation.get("description") or ""),
                    "operation_type": str(
                        step_operation.get("operation_type")
                        or operation_cfg.get("operationType")
                        or ""
                    ),
                    "configuration_json": operation_cfg,
                    "_ui_key": _new_ui_key(),
                }
            )

        step_cfg = (
            scenario_step.get("configuration_json")
            if isinstance(scenario_step.get("configuration_json"), dict)
            else {}
        )
        draft_steps.append(
            {
                "id": scenario_step.get("id"),
                "order": _safe_int(scenario_step.get("order"), step_idx + 1),
                "code": str(scenario_step.get("code") or ""),
                "description": str(scenario_step.get("description") or ""),
                "step_type": str(
                    scenario_step.get("step_type")
                    or step_cfg.get("stepType")
                    or ""
                ),
                "configuration_json": step_cfg,
                "on_failure": str(scenario_step.get("on_failure") or "ABORT"),
                "operations": draft_operations,
                "_ui_key": _new_ui_key(),
                "_edit_mode": False,
            }
        )

    return {
        "id": scenario.get("id"),
        "code": str(scenario.get("code") or ""),
        "description": str(scenario.get("description") or ""),
        "steps": draft_steps,
    }


def _refresh_all(force: bool = False):
    load_scenarios_context(force=force)


def _ensure_editor_context():
    _refresh_all(force=False)
    scenarios = st.session_state.get(SCENARIOS_KEY, [])
    mode = str(st.session_state.get(SCENARIO_EDITOR_MODE_KEY, "edit"))
    selected_id = _resolve_selected_scenario_id(scenarios)
    draft = st.session_state.get(SCENARIO_DRAFT_KEY)

    if mode == "create":
        if not isinstance(draft, dict):
            _set_editor_draft(_new_scenario_draft(), "create")
        return

    if not selected_id:
        _set_editor_draft(None, "edit")
        return

    if not isinstance(draft, dict) or str(draft.get("id")) != str(selected_id):
        new_draft = _build_scenario_draft(selected_id)
        _set_editor_draft(new_draft, "edit")


def _build_scenario_payload(draft: dict) -> dict:
    steps_payload: list[dict] = []
    for step in draft.get("steps") or []:
        operations_payload: list[dict] = []
        for operation in step.get("operations") or []:
            operations_payload.append(
                {
                    "order": _safe_int(operation.get("order"), 0),
                    "code": str(operation.get("code") or "").strip(),
                    "description": str(operation.get("description") or ""),
                    "cfg": (
                        operation.get("configuration_json")
                        if isinstance(operation.get("configuration_json"), dict)
                        else {}
                    ),
                }
            )

        steps_payload.append(
            {
                "order": _safe_int(step.get("order"), 0),
                "code": str(step.get("code") or "").strip(),
                "description": str(step.get("description") or ""),
                "cfg": (
                    step.get("configuration_json")
                    if isinstance(step.get("configuration_json"), dict)
                    else {}
                ),
                "on_failure": str(step.get("on_failure") or "ABORT"),
                "operations": operations_payload,
            }
        )

    return {
        "code": str(draft.get("code") or "").strip(),
        "description": str(draft.get("description") or ""),
        "steps": steps_payload,
    }


def _validate_draft(draft: dict) -> str | None:
    payload = _build_scenario_payload(draft)
    if not payload["code"]:
        return "Il campo Code e' obbligatorio."

    for idx, step in enumerate(payload["steps"]):
        if not step["code"]:
            return f"Scenario step #{idx + 1}: code obbligatorio."
        if not isinstance(step.get("cfg"), dict) or not step["cfg"].get("stepType"):
            return f"Scenario step #{idx + 1}: configurazione step non valida."
        step_type = str(step["cfg"].get("stepType") or "").strip().replace("_", "-").lower()
        if step_type == STEP_TYPE_SLEEP:
            return f"Scenario step #{idx + 1}: stepType '{STEP_TYPE_SLEEP}' non supportato."
        if step["on_failure"] not in ON_FAILURE_OPTIONS:
            return (
                f"Scenario step #{idx + 1}: on_failure deve essere uno tra "
                f"{', '.join(ON_FAILURE_OPTIONS)}."
            )
        for op_idx, operation in enumerate(step["operations"]):
            if not operation["code"]:
                return (
                    f"Scenario step #{idx + 1}, operation #{op_idx + 1}: "
                    "code obbligatorio."
                )
            if not isinstance(operation.get("cfg"), dict) or not operation["cfg"].get("operationType"):
                return (
                    f"Scenario step #{idx + 1}, operation #{op_idx + 1}: "
                    "configurazione operation non valida."
                )
    return None


def _save_draft(preserve_existing_feedback: bool = False):
    draft = st.session_state.get(SCENARIO_DRAFT_KEY)
    if not isinstance(draft, dict):
        st.error("Nessuno scenario in modifica.")
        return

    validation_error = _validate_draft(draft)
    if validation_error:
        st.error(validation_error)
        return

    mode = str(st.session_state.get(SCENARIO_EDITOR_MODE_KEY, "edit"))
    payload = _build_scenario_payload(draft)

    try:
        if mode == "create" or not draft.get("id"):
            response = create_scenario(payload)
            scenario_id = response.get("id") if isinstance(response, dict) else None
            feedback = "Scenario creato."
        else:
            scenario_id = str(draft.get("id"))
            update_scenario(
                {
                    "id": scenario_id,
                    **payload,
                },
            )
            feedback = "Scenario aggiornato."
    except Exception as exc:
        st.error(f"Errore salvataggio scenario: {str(exc)}")
        return

    _refresh_all(force=True)
    if scenario_id:
        st.session_state[SELECTED_SCENARIO_ID_KEY] = str(scenario_id)
        updated_draft = _build_scenario_draft(str(scenario_id))
    else:
        updated_draft = None
    _set_editor_draft(updated_draft, "edit")
    existing_feedback = str(st.session_state.get(SCENARIO_FEEDBACK_KEY) or "").strip()
    if not preserve_existing_feedback or not existing_feedback:
        st.session_state[SCENARIO_FEEDBACK_KEY] = feedback
    st.rerun()


def _auto_save_draft_after_change():
    _save_draft(preserve_existing_feedback=True)


def _delete_scenario(scenario_id: str):
    try:
        delete_scenario_by_id(scenario_id)
    except Exception as exc:
        st.error(f"Errore cancellazione scenario: {str(exc)}")
        return

    _refresh_all(force=True)
    scenarios = st.session_state.get(SCENARIOS_KEY, [])
    selected_id = _resolve_selected_scenario_id(scenarios)
    if selected_id:
        updated_draft = _build_scenario_draft(selected_id)
        _set_editor_draft(updated_draft, "edit")
    else:
        _set_editor_draft(None, "edit")
    st.session_state[SCENARIO_FEEDBACK_KEY] = "Scenario eliminato."
    st.rerun()


def _delete_scenario_execution(execution_id: str):
    execution_id_value = str(execution_id or "").strip()
    if not execution_id_value:
        st.error("Execution non valida.")
        return
    try:
        delete_scenario_execution_by_id(execution_id_value)
    except Exception as exc:
        st.error(f"Errore cancellazione execution: {str(exc)}")
        return
    st.rerun()


def _refresh_scenario_execution_selector_state(
    scenario_id: str,
    preferred_execution_id: str = "",
):
    scenario_id_value = str(scenario_id or "").strip()
    if not scenario_id_value:
        return

    preferred_execution_id_value = str(preferred_execution_id or "").strip()
    cached_executions = st.session_state.get(SCENARIO_EDITOR_EXECUTIONS_KEY) or []

    try:
        executions = get_scenario_executions(scenario_id=scenario_id_value, limit=200)
    except Exception:
        executions = cached_executions if isinstance(cached_executions, list) else []

    executions = [item for item in executions if isinstance(item, dict)]
    execution_ids = [str(item.get("id") or "").strip() for item in executions if item.get("id")]

    if preferred_execution_id_value and preferred_execution_id_value not in execution_ids:
        draft = st.session_state.get(SCENARIO_DRAFT_KEY)
        synthetic_execution = {
            "id": preferred_execution_id_value,
            "scenario_id": scenario_id_value,
            "scenario_code": str((draft or {}).get("code") or ""),
            "scenario_description": str((draft or {}).get("description") or ""),
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "steps": [],
        }
        executions.insert(0, synthetic_execution)

    st.session_state[SCENARIO_EDITOR_EXECUTIONS_KEY] = executions
    if preferred_execution_id_value:
        st.session_state[SCENARIO_SELECTED_EXECUTION_ID_KEY] = preferred_execution_id_value
        st.session_state[SCENARIO_LAST_EXECUTION_ID_KEY] = preferred_execution_id_value
        st.session_state[
            f"scenario_editor_execution_select_{scenario_id_value}"
        ] = preferred_execution_id_value


def _execute_scenario(scenario_id: str):
    st.session_state[SCENARIO_LAST_EXECUTION_ID_KEY] = ""
    try:
        response = execute_scenario_by_id(scenario_id)
    except Exception as exc:
        st.error(f"Errore esecuzione scenario: {str(exc)}")
        return

    execution_id = str((response or {}).get("execution_id") or "").strip()
    if execution_id:
        register_execution_listener(execution_id, scenario_id)
    _refresh_scenario_execution_selector_state(
        scenario_id=scenario_id,
        preferred_execution_id=execution_id,
    )

    st.session_state[SCENARIO_FEEDBACK_KEY] = "Scenario avviato."
    st.rerun()


def _execute_scenario_step(
    scenario_id: str,
    scenario_step_id: str,
    include_previous: bool,
):
    st.session_state[SCENARIO_LAST_EXECUTION_ID_KEY] = ""
    try:
        response = execute_scenario_step_by_id(
            scenario_id=scenario_id,
            scenario_step_id=scenario_step_id,
            include_previous=include_previous,
        )
    except Exception as exc:
        st.error(f"Error executing scenario step: {str(exc)}")
        return

    execution_id = str((response or {}).get("execution_id") or "").strip()
    if execution_id:
        register_execution_listener(execution_id, scenario_id)
    _refresh_scenario_execution_selector_state(
        scenario_id=scenario_id,
        preferred_execution_id=execution_id,
    )
    st.session_state[SCENARIO_FEEDBACK_KEY] = "Scenario step started."
    st.rerun()


def _execute_scenario_step_from_draft(
    scenario_step: dict,
    include_previous: bool,
):
    draft = st.session_state.get(SCENARIO_DRAFT_KEY)
    if not isinstance(draft, dict):
        st.error("Scenario not loaded.")
        return
    scenario_id = str(draft.get("id") or "").strip()
    scenario_step_id = str((scenario_step or {}).get("id") or "").strip()
    if not scenario_id or not scenario_step_id:
        st.error("Selected step is not available. Save the scenario and retry.")
        return
    _execute_scenario_step(
        scenario_id=scenario_id,
        scenario_step_id=scenario_step_id,
        include_previous=include_previous,
    )


def _update_scenario_description(scenario_id: str, new_description: str):
    scenario_id = str(scenario_id or "").strip()
    if not scenario_id:
        st.error("Scenario non valido.")
        return

    draft = _build_scenario_draft(scenario_id)
    if not isinstance(draft, dict):
        st.error("Errore caricamento scenario.")
        return

    draft["description"] = str(new_description or "")
    payload = _build_scenario_payload(draft)

    try:
        update_scenario(
            {
                "id": scenario_id,
                **payload,
            },
        )
    except Exception as exc:
        st.error(f"Errore aggiornamento descrizione: {str(exc)}")
        return

    load_scenarios(force=True)
    st.session_state[SCENARIO_FEEDBACK_KEY] = "Descrizione scenario aggiornata."
    st.rerun()


def _create_scenario_from_list(code: str, description: str):
    code_value = str(code or "").strip()
    if not code_value:
        st.error("Il campo Code e' obbligatorio.")
        return

    payload = {
        "code": code_value,
        "description": str(description or ""),
        "steps": [],
    }
    try:
        response = create_scenario(payload)
    except Exception as exc:
        st.error(f"Errore creazione scenario: {str(exc)}")
        return

    scenario_id = str((response or {}).get("id") or "").strip()
    if not scenario_id:
        st.error("Errore creazione scenario: id non restituito.")
        return

    _refresh_all(force=True)
    st.session_state[SELECTED_SCENARIO_ID_KEY] = scenario_id
    updated_draft = _build_scenario_draft(scenario_id)
    if not isinstance(updated_draft, dict):
        st.error("Errore caricamento dettaglio scenario.")
        return
    _set_editor_draft(updated_draft, "edit")
    st.session_state[SCENARIO_FEEDBACK_KEY] = "Scenario creato."
    st.switch_page(SCENARIO_EDITOR_PAGE_PATH)


@st.dialog("Nuovo scenario")
def _create_scenario_list_dialog(dialog_suffix: str):
    code_key = f"scenario_list_create_code_{dialog_suffix}"
    description_key = f"scenario_list_create_description_{dialog_suffix}"
    code = st.text_input(
        "Code",
        key=code_key,
    )
    description = st.text_area(
        "Description",
        key=description_key,
        height=180,
    )

    action_cols = st.columns([1,1, 1], gap="small", vertical_alignment="center")
    with action_cols[1]:
        if st.button(
            "Save",
            key=f"scenario_list_create_save_{dialog_suffix}",
            icon=":material/save:",
            type="secondary",
            use_container_width=True,
        ):
            _create_scenario_from_list(code, description)
    with action_cols[2]:
        if st.button(
            "Cancel",
            key=f"scenario_list_create_cancel_{dialog_suffix}",
            use_container_width=True,
        ):
            st.rerun()


@st.dialog("Azioni scenario")
def _scenario_list_actions_dialog(
    scenario_id: str,
    current_description: str,
    dialog_suffix: str,
):
    input_key = f"scenario_list_actions_description_input_{dialog_suffix}"
    new_description = st.text_area(
        "Description",
        value=current_description,
        key=input_key,
        height=180,
    )

    action_cols = st.columns([3, 3, 2], gap="small", vertical_alignment="center")
    with action_cols[0]:
        if st.button(
            "Save description",
            key=f"scenario_list_actions_save_{dialog_suffix}",
            icon=":material/save:",
            type="secondary",
            use_container_width=True,
        ):
            _update_scenario_description(scenario_id, new_description)
    with action_cols[1]:
        if st.button(
            "Delete scenario",
            key=f"scenario_list_actions_delete_{dialog_suffix}",
            icon=":material/delete:",
            type="secondary",
            use_container_width=True,
        ):
            _delete_scenario(scenario_id)
    with action_cols[2]:
        if st.button(
            "Cancel",
            key=f"scenario_list_actions_cancel_{dialog_suffix}",
            use_container_width=True,
        ):
            st.rerun()

def _open_scenario_editor_for_edit(scenario_id: str, execution_id: str | None = None):
    scenario_id = str(scenario_id or "").strip()
    if not scenario_id:
        st.error("Scenario non valido.")
        return

    st.session_state[SELECTED_SCENARIO_ID_KEY] = scenario_id
    draft = _build_scenario_draft(scenario_id)
    if draft is None:
        st.error("Errore caricamento dettaglio scenario.")
        return

    _set_editor_draft(draft, "edit")
    execution_id_value = str(execution_id or "").strip()
    if execution_id_value:
        st.session_state[SCENARIO_SELECTED_EXECUTION_ID_KEY] = execution_id_value
        st.session_state[SCENARIO_LAST_EXECUTION_ID_KEY] = execution_id_value
        st.session_state[f"scenario_editor_execution_select_{scenario_id}"] = execution_id_value
    st.switch_page(SCENARIO_EDITOR_PAGE_PATH)


def _render_operation_component(
    scenario_step: dict,
    operation: dict,
    op_idx: int,
    step_ui_key: str,
    nonce: int,
    operation_status: str = "idle",
    operation_error_message: str = "",
):
    operation_render_component(
        scenario_step,
        operation,
        op_idx,
        step_ui_key,
        nonce,
        operation_status=operation_status,
        operation_error_message=operation_error_message,
        persist_scenario_changes_fn=_auto_save_draft_after_change,
    )


def _render_step_component(
    draft: dict,
    scenario_step: dict,
    step_idx: int,
    nonce: int,
    step_catalog: list[dict],
    step_labels_by_id: dict[str, str],
    execution_state: dict,
):
    step_render_component(
        draft,
        scenario_step,
        step_idx,
        nonce,
        step_catalog,
        step_labels_by_id,
        ON_FAILURE_OPTIONS,
        _render_operation_component,
        _open_add_new_step_operation_dialog,
        _execute_scenario_step_from_draft,
        lambda step_item: _get_step_execution_status(execution_state, step_item),
        lambda step_item, operation_item: _get_operation_execution_status(
            execution_state,
            step_item,
            operation_item,
        ),
        lambda step_item: _get_step_execution_error_message(execution_state, step_item),
        lambda step_item, operation_item: _get_operation_execution_error_message(
            execution_state,
            step_item,
            operation_item,
        ),
        persist_scenario_changes_fn=_auto_save_draft_after_change,
    )


def _render_add_scenario_step_dialog(
    draft: dict,
    step_catalog: list[dict],
    step_labels_by_id: dict[str, str],
):
    step_render_add_dialog(
        draft,
        step_catalog,
        step_labels_by_id,
        _close_add_scenario_step_dialog,
        persist_scenario_changes_fn=_auto_save_draft_after_change,
    )


@st.dialog("Add step", width="large")
def _add_scenario_step_dialog(
    draft: dict,
    step_catalog: list[dict],
    step_labels_by_id: dict[str, str],
):
    _render_add_scenario_step_dialog(draft, step_catalog, step_labels_by_id)


def _render_import_step_operation_dialog(
    draft: dict,
    operation_catalog: list[dict],
    operation_labels_by_id: dict[str, str],
):
    operation_render_add_dialog(
        draft,
        operation_catalog,
        operation_labels_by_id,
        _close_add_step_operation_dialog,
        persist_scenario_changes_fn=_auto_save_draft_after_change,
    )


@st.dialog("Add operation", width="large")
def _add_step_operation_dialog(
    draft: dict,
    operation_catalog: list[dict],
    operation_labels_by_id: dict[str, str],
):
    _render_import_step_operation_dialog(draft, operation_catalog, operation_labels_by_id)


def _render_editor():
    draft = st.session_state.get(SCENARIO_DRAFT_KEY)
    if not isinstance(draft, dict):
        return

    execution_state = _get_execution_state_for_current_scenario()

    nonce = int(st.session_state.get(SCENARIO_EDITOR_NONCE_KEY, 0))
    step_catalog = st.session_state.get(STEPS_CATALOG_KEY, [])
    operation_catalog = st.session_state.get(OPERATIONS_CATALOG_KEY, [])

    step_labels_by_id = {
        str(item.get("id")): _step_catalog_label(item)
        for item in step_catalog
        if item.get("id")
    }
    operation_labels_by_id = {
        str(item.get("id")): _operation_catalog_label(item)
        for item in operation_catalog
        if item.get("id")
    }

    steps = draft.get("steps") or []

    for step_idx, scenario_step in enumerate(steps):
        _render_step_component(
            draft,
            scenario_step,
            step_idx,
            nonce,
            step_catalog,
            step_labels_by_id,
            execution_state,
        )

    if st.session_state.get(ADD_SCENARIO_STEP_DIALOG_OPEN_KEY, False):
        _add_scenario_step_dialog(draft, step_catalog, step_labels_by_id)
    if st.session_state.get(ADD_STEP_OPERATION_DIALOG_OPEN_KEY, False):
        _add_step_operation_dialog(draft, operation_catalog, operation_labels_by_id)


def _render_execution_step_details(step_execution: dict, step_idx: int):
    step_code = str(step_execution.get("step_code") or "").strip()
    step_description = str(step_execution.get("step_description") or "").strip()
    step_label = step_description or step_code or "-"
    step_number = _safe_int(step_execution.get("step_order"), step_idx + 1)
    step_status = _execution_status_label(str(step_execution.get("status") or ""))
    step_time = _format_time_only(step_execution.get("started_at"))
    step_feedback = f"[{step_time}] Step #{step_number} : {step_label}"
    step_error_message = str(step_execution.get("error_message") or "").strip()
    if step_status == "error":
        st.error(step_feedback)
        if step_error_message:
            st.error(step_error_message)
    elif step_status == "success":
        st.success(step_feedback)
    elif step_status == "running":
        st.info(step_feedback)
    else:
        st.info(step_feedback)
        if step_error_message:
            st.error(step_error_message)

    operation_executions = step_execution.get("operations") or []
    if not isinstance(operation_executions, list) or not operation_executions:
        return
    for op_idx, operation_execution in enumerate(operation_executions):
        operation_code = str(operation_execution.get("operation_code") or "").strip()
        operation_description = str(operation_execution.get("operation_description") or "").strip()
        operation_label = operation_description or operation_code or "-"
        operation_number = _safe_int(operation_execution.get("operation_order"), op_idx + 1)
        operation_status = _execution_status_label(str(operation_execution.get("status") or ""))
        operation_time = _format_time_only(operation_execution.get("started_at"))
        operation_feedback = f"[{operation_time}] Operazione #{operation_number} : {operation_label}"
        operation_error_message = str(operation_execution.get("error_message") or "").strip()

        if operation_status == "error":
            st.error(operation_feedback)
            if operation_error_message:
                st.error(operation_error_message)
        elif operation_status == "success":
            st.success(operation_feedback)
        elif operation_status == "running":
            st.info(operation_feedback)
        else:
            st.info(operation_feedback)
            if operation_error_message:
                st.error(operation_error_message)


def _count_execution_steps(step_executions: list[dict]) -> tuple[int, int]:
    success_count = 0
    error_count = 0
    for step_execution in step_executions:
        if not isinstance(step_execution, dict):
            continue
        status = _execution_status_label(str(step_execution.get("status") or ""))
        if status == "success":
            success_count += 1
        elif status == "error":
            error_count += 1
    return success_count, error_count


def _render_execution_details(execution_payload: dict):
    step_executions = execution_payload.get("steps") or []
    if not isinstance(step_executions, list) or not step_executions:
        st.caption("Nessun dettaglio step.")
        return

    success_steps, error_steps = _count_execution_steps(step_executions)
    st.markdown(f"{success_steps} step eseguiti con successo")
    st.markdown(f"{error_steps} step eseguiti con errore")
    st.divider()

    for step_execution_idx, step_execution in enumerate(step_executions):
        if not isinstance(step_execution, dict):
            continue
        _render_execution_step_details(
            step_execution=step_execution,
            step_idx=step_execution_idx,
        )
        if step_execution_idx < len(step_executions) - 1:
            st.divider()


def _render_execution_summary_row(
    scenario_id: str,
    execution_id: str,
    expander_title: str,
    execution_payload: dict,
    status: str,
    idx: int,
):
    summary_cols = st.columns([1, 10, 1, 1], gap="small", vertical_alignment="top")
    with summary_cols[0]:
        st.button(
            "",
            key=f"home_execution_status_{execution_id or idx}",
            icon=_execution_status_icon(status),
            help=f"Status execution: {status}",
            type="tertiary",
            use_container_width=True,
            disabled=True,
        )
    with summary_cols[1]:
        with st.expander(expander_title, expanded=False):
            _render_execution_details(
                execution_payload=execution_payload,
            )
    with summary_cols[2]:
        if st.button(
            "",
            key=f"home_open_scenario_editor_{execution_id or idx}",
            icon=":material/open_in_new:",
            help="Apri scenario editor",
            type="tertiary",
            use_container_width=True,
            disabled=not bool(scenario_id),
        ):
            _open_scenario_editor_for_edit(scenario_id, execution_id=execution_id)
    with summary_cols[3]:
        if st.button(
            "",
            key=f"home_delete_execution_{execution_id or idx}",
            icon=":material/delete:",
            help="Elimina execution",
            type="tertiary",
            use_container_width=True,
            disabled=not bool(execution_id),
        ):
            _delete_scenario_execution(execution_id)


def _render_step_toolbar(execution_state: dict):
    draft = st.session_state.get(SCENARIO_DRAFT_KEY)
    scenario_id = str((draft or {}).get("id") or "").strip()
    scenario_is_saved = bool(scenario_id)
    nonce = int(st.session_state.get(SCENARIO_EDITOR_NONCE_KEY, 0))
    action_cols = st.columns([5, 2, 2, 5], gap="small", vertical_alignment="bottom")
    with action_cols[0]:
        if isinstance(execution_state, dict) and execution_state:
            is_running = bool(execution_state.get("running"))
            executed_steps = int(execution_state.get("executed_steps") or 0)
            total_steps = int(execution_state.get("total_steps") or 0)
            if total_steps > 0 or is_running:
                status_label = (
                    "running" if is_running else str(execution_state.get("status") or "finished")
                )
                st.caption(
                    f"Test scenario {status_label}: {executed_steps}/{total_steps} step executed"
                )

    with action_cols[1]:
        if st.button(
            "",
            help="Aggiungi uno step allo scenario.",
            key=f"scenario_{nonce}_add_step",
            icon=":material/add:",
            use_container_width=True
        ):
            _open_add_scenario_step_dialog()
            st.rerun()
    with action_cols[2]:
        if st.button(
            "",
            help="Esegui l'intero scenario.",
            key=f"scenario_{nonce}_execute_all_steps",
            icon=":material/play_arrow:",
            use_container_width=True,
            disabled=not scenario_is_saved,
        ):
            _execute_scenario(scenario_id)


def _execution_select_label(execution_payload: dict) -> str:
    execution_id = str(execution_payload.get("id") or "").strip()
    status = _execution_status_label(str(execution_payload.get("status") or ""))
    started_at = _format_datetime_compact(execution_payload.get("started_at"))
    short_id = execution_id[:8] if execution_id else "-"
    return f"{started_at} | {status} | {short_id}"


def _build_execution_state_from_payload(execution_payload: dict) -> dict:
    status = _execution_status_label(str(execution_payload.get("status") or ""))
    steps = execution_payload.get("steps") or []
    step_status: dict[str, str] = {}
    step_error: dict[str, str] = {}
    operation_status: dict[str, str] = {}
    operation_error: dict[str, str] = {}
    executed_steps = 0

    if isinstance(steps, list):
        for step_execution in steps:
            if not isinstance(step_execution, dict):
                continue
            scenario_step_id = str(step_execution.get("scenario_step_id") or "").strip()
            resolved_step_status = _execution_status_label(str(step_execution.get("status") or ""))
            if resolved_step_status in {"success", "error"}:
                executed_steps += 1
            if scenario_step_id:
                step_status[scenario_step_id] = resolved_step_status
                if resolved_step_status == "error":
                    step_error_message = str(step_execution.get("error_message") or "").strip()
                    if step_error_message:
                        step_error[scenario_step_id] = step_error_message

            operations = step_execution.get("operations") or []
            if not isinstance(operations, list):
                continue
            for operation_execution in operations:
                if not isinstance(operation_execution, dict):
                    continue
                step_operation_id = str(operation_execution.get("step_operation_id") or "").strip()
                if not scenario_step_id or not step_operation_id:
                    continue
                key = f"{scenario_step_id}:{step_operation_id}"
                resolved_operation_status = _execution_status_label(
                    str(operation_execution.get("status") or "")
                )
                operation_status[key] = resolved_operation_status
                if resolved_operation_status == "error":
                    operation_error_message = str(
                        operation_execution.get("error_message") or ""
                    ).strip()
                    if operation_error_message:
                        operation_error[key] = operation_error_message

    return {
        "running": status == "running",
        "status": status,
        "scenario_id": str(execution_payload.get("scenario_id") or "").strip(),
        "execution_id": str(execution_payload.get("id") or "").strip(),
        "executed_steps": executed_steps,
        "total_steps": len(steps) if isinstance(steps, list) else 0,
        "step_status": step_status,
        "step_error": step_error,
        "operation_status": operation_status,
        "operation_error": operation_error,
        "error": str(execution_payload.get("error_message") or "").strip() or None,
    }


def _render_scenario_execution_selector(scenario_id: str):
    scenario_id_value = str(scenario_id or "").strip()
    if not scenario_id_value:
        return
    executions: list[dict]
    try:
        executions = get_scenario_executions(scenario_id=scenario_id_value, limit=200)
    except Exception as exc:
        st.error(f"Errore caricamento executions: {str(exc)}")
        st.session_state[SCENARIO_EDITOR_EXECUTIONS_KEY] = []
        st.session_state[SCENARIO_SELECTED_EXECUTION_ID_KEY] = ""
        st.session_state[SCENARIO_LAST_EXECUTION_ID_KEY] = ""
        return

    executions = [item for item in executions if isinstance(item, dict)]
    preferred_execution_id = str(
        st.session_state.get(SCENARIO_SELECTED_EXECUTION_ID_KEY)
        or st.session_state.get(SCENARIO_LAST_EXECUTION_ID_KEY)
        or ""
    ).strip()

    execution_ids = [str(item.get("id") or "").strip() for item in executions if item.get("id")]
    execution_ids = [item for item in execution_ids if item]
    if preferred_execution_id and preferred_execution_id not in execution_ids:
        draft = st.session_state.get(SCENARIO_DRAFT_KEY)
        synthetic_execution = {
            "id": preferred_execution_id,
            "scenario_id": scenario_id_value,
            "scenario_code": str((draft or {}).get("code") or ""),
            "scenario_description": str((draft or {}).get("description") or ""),
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "steps": [],
        }
        executions.insert(0, synthetic_execution)
        execution_ids.insert(0, preferred_execution_id)

    st.session_state[SCENARIO_EDITOR_EXECUTIONS_KEY] = executions

    if not execution_ids:
        st.caption("Nessuna execution")
        st.session_state[SCENARIO_SELECTED_EXECUTION_ID_KEY] = ""
        st.session_state[SCENARIO_LAST_EXECUTION_ID_KEY] = ""
        return

    labels_by_id = {
        str(item.get("id") or "").strip(): _execution_select_label(item)
        for item in executions
        if item.get("id")
    }

    if preferred_execution_id not in execution_ids:
        preferred_execution_id = execution_ids[0]

    select_key = f"scenario_editor_execution_select_{scenario_id_value}"
    current_value = str(st.session_state.get(select_key) or "").strip()
    if current_value not in execution_ids:
        st.session_state[select_key] = preferred_execution_id

    selected_execution_id = st.selectbox(
        "Execution",
        options=execution_ids,
        key=select_key,
        format_func=lambda execution_id: labels_by_id.get(execution_id, execution_id),
    )
    st.session_state[SCENARIO_SELECTED_EXECUTION_ID_KEY] = str(selected_execution_id or "").strip()
    st.session_state[SCENARIO_LAST_EXECUTION_ID_KEY] = str(selected_execution_id or "").strip()


@st.dialog("Modifica descrizione scenario")
def _edit_scenario_description_dialog(current_description: str, dialog_suffix: str):
    input_key = f"scenario_edit_description_input_{dialog_suffix}"
    edited_description = st.text_area(
        "Description",
        value=current_description,
        key=input_key,
        height=180,
    )

    action_cols = st.columns([2, 2, 6], gap="small", vertical_alignment="center")
    with action_cols[0]:
        if st.button(
            "Save",
            key=f"scenario_edit_description_save_{dialog_suffix}",
            icon=":material/save:",
            type="secondary",
            use_container_width=True,
        ):
            draft = st.session_state.get(SCENARIO_DRAFT_KEY)
            if isinstance(draft, dict):
                draft["description"] = edited_description
            st.rerun()
    with action_cols[1]:
        if st.button(
            "Cancel",
            key=f"scenario_edit_description_cancel_{dialog_suffix}",
            use_container_width=True,
        ):
            st.rerun()


def _get_execution_state_for_current_scenario() -> dict:
    draft = st.session_state.get(SCENARIO_DRAFT_KEY)
    if not isinstance(draft, dict):
        return {}
    scenario_id = str(draft.get("id") or "").strip()
    if not scenario_id:
        return {}

    execution_id = str(
        st.session_state.get(SCENARIO_SELECTED_EXECUTION_ID_KEY)
        or st.session_state.get(SCENARIO_LAST_EXECUTION_ID_KEY)
        or ""
    ).strip()
    if not execution_id:
        return {}
    live_state = get_execution_state(execution_id)
    if isinstance(live_state, dict):
        if str(live_state.get("scenario_id") or "").strip() == scenario_id:
            return live_state

    executions = st.session_state.get(SCENARIO_EDITOR_EXECUTIONS_KEY) or []
    if not isinstance(executions, list):
        return {}
    for execution_payload in executions:
        if not isinstance(execution_payload, dict):
            continue
        payload_execution_id = str(execution_payload.get("id") or "").strip()
        payload_scenario_id = str(execution_payload.get("scenario_id") or "").strip()
        if payload_execution_id == execution_id and payload_scenario_id == scenario_id:
            return _build_execution_state_from_payload(execution_payload)
    return {}


def _get_step_execution_status(execution_state: dict, scenario_step: dict) -> str:
    scenario_step_id = str(scenario_step.get("id") or "").strip()
    if not scenario_step_id:
        return "idle"
    statuses = execution_state.get("step_status") if isinstance(execution_state, dict) else {}
    return str((statuses or {}).get(scenario_step_id) or "idle")


def _get_step_execution_error_message(execution_state: dict, scenario_step: dict) -> str:
    scenario_step_id = str(scenario_step.get("id") or "").strip()
    if not scenario_step_id:
        return ""
    errors = execution_state.get("step_error") if isinstance(execution_state, dict) else {}
    return str((errors or {}).get(scenario_step_id) or "")


def _get_operation_execution_status(
    execution_state: dict,
    scenario_step: dict,
    operation: dict,
) -> str:
    scenario_step_id = str(scenario_step.get("id") or "").strip()
    operation_id = str(operation.get("id") or "").strip()
    if not scenario_step_id or not operation_id:
        return "idle"
    key = f"{scenario_step_id}:{operation_id}"
    statuses = execution_state.get("operation_status") if isinstance(execution_state, dict) else {}
    return str((statuses or {}).get(key) or "idle")


def _get_operation_execution_error_message(
    execution_state: dict,
    scenario_step: dict,
    operation: dict,
) -> str:
    scenario_step_id = str(scenario_step.get("id") or "").strip()
    operation_id = str(operation.get("id") or "").strip()
    if not scenario_step_id or not operation_id:
        return ""
    key = f"{scenario_step_id}:{operation_id}"
    errors = execution_state.get("operation_error") if isinstance(execution_state, dict) else {}
    return str((errors or {}).get(key) or "")


def render_scenarios_list_page():
    load_scenarios(force=False)
    scenarios = st.session_state.get(SCENARIOS_KEY, [])

    st.header("Scenarios")
    st.caption("Lista scenari con azioni rapide.")
    st.divider()

    header_cols = st.columns([9, 1], gap="small", vertical_alignment="center")
    with header_cols[1]:
        if st.button(
            "",
            key="add_scenario_list_btn",
            icon=":material/add:",
            help="Nuovo scenario",
            use_container_width=True,
        ):
            _create_scenario_list_dialog(dialog_suffix="header")

    if not scenarios:
        st.info("Nessuno scenario configurato.")
        _render_feedback()
        return

    for idx, scenario in enumerate(scenarios):
        scenario_id = str(scenario.get("id") or "")
        code = str(scenario.get("code") or "-")
        description = str(scenario.get("description") or code)
        label = f"{description}" if description != code else code

        with st.container(border=True):
            row_cols = st.columns([8, 1, 1], gap="small", vertical_alignment="center")
            with row_cols[0]:
                st.write(label)
            with row_cols[1]:
                if st.button(
                    "",
                    key=f"edit_scenario_list_btn_{scenario_id or idx}",
                    icon=":material/settings:",
                    help="Modifica scenario",
                    use_container_width=True,
                ):
                    _open_scenario_editor_for_edit(scenario_id)
            with row_cols[2]:
                if st.button(
                    "",
                    key=f"scenario_actions_list_btn_{scenario_id or idx}",
                    icon=":material/more_vert:",
                    help="Azioni scenario",
                    use_container_width=True,
                ):
                    _scenario_list_actions_dialog(
                        scenario_id=scenario_id,
                        current_description=str(scenario.get("description") or ""),
                        dialog_suffix=f"{scenario_id or idx}",
                    )

    _render_feedback()


def render_scenario_editor_page():
    _ensure_editor_context()

    header_cols = st.columns([8, 2], gap="small", vertical_alignment="center")
    with header_cols[1]:
        if st.button(
            "Back",
            key="scenario_editor_back_btn",
            icon=":material/arrow_back:",
            use_container_width=True,
        ):
            st.switch_page(SCENARIOS_LIST_PAGE_PATH)

    if not isinstance(st.session_state.get(SCENARIO_DRAFT_KEY), dict):
        st.info("Nessuno scenario selezionato.")
        if st.button(
            "Nuovo scenario",
            key="scenario_editor_create_btn",
            icon=":material/add:",
            type="secondary",
        ):
            _create_scenario_list_dialog(dialog_suffix="editor")
        _render_feedback()
        return

    scenario = st.session_state.get(SCENARIO_DRAFT_KEY)
    description = str(scenario.get("description") or "").strip() or "-"
    scenario_id = str(scenario.get("id") or "").strip()
    title_cols = st.columns([8, 3], gap="small", vertical_alignment="bottom")
    with title_cols[0]:
        st.title(description)
    with title_cols[1]:
        if scenario_id:
            _render_scenario_execution_selector(scenario_id)

    st.divider()
    _render_editor()

    st.divider()
    execution_state = _get_execution_state_for_current_scenario()
    _render_step_toolbar(execution_state)
        

    execution_state = _get_execution_state_for_current_scenario()
    _render_feedback()
    if bool((execution_state or {}).get("running")):
        time.sleep(1)
        st.rerun()

def _render_feedback():
    feedback_message = st.session_state.pop(SCENARIO_FEEDBACK_KEY, None)
    if feedback_message:
        st.success(feedback_message, icon=":material/check_circle:")

def render_home_page():
    st.header("Home")
    st.subheader("Test scenario executions")
    executions = get_scenario_executions(limit=50)

    if not executions:
        st.caption("Nessuna execution disponibile.")
        return

    for idx, execution_payload in enumerate(executions):
        if not isinstance(execution_payload, dict):
            continue
        scenario_id = str(execution_payload.get("scenario_id") or "").strip()
        execution_id = str(execution_payload.get("id") or "").strip()
        scenario_name = str(
            execution_payload.get("scenario_description")
            or execution_payload.get("scenario_code")
            or "Scenario"
        ).strip()
        status = _execution_status_label(str(execution_payload.get("status") or ""))
        started_at = _format_datetime_compact(execution_payload.get("started_at"))
        expander_title = f"{started_at} {scenario_name}"
        _render_execution_summary_row(
            scenario_id=scenario_id,
            execution_id=execution_id,
            expander_title=expander_title,
            execution_payload=execution_payload,
            status=status,
            idx=idx,
        )


def render_scenarios_page():
    render_scenarios_list_page()
