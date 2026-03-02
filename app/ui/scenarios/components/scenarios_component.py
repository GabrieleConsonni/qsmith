from decimal import Decimal
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
    SCENARIO_FEEDBACK_KEY,
    SCENARIO_LAST_EXECUTION_ID_KEY,
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


def _execution_status_label(status: str) -> str:
    normalized = str(status or "").strip().lower()
    if normalized == "success":
        return "success"
    if normalized == "error":
        return "error"
    if normalized == "running":
        return "running"
    return normalized or "unknown"


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
        st.session_state[SCENARIO_LAST_EXECUTION_ID_KEY] = execution_id

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
        st.session_state[SCENARIO_LAST_EXECUTION_ID_KEY] = execution_id
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


@st.dialog("Modifica descrizione")
def _edit_scenario_description_list_dialog(
    scenario_id: str,
    current_description: str,
    dialog_suffix: str,
):
    input_key = f"scenario_list_edit_description_input_{dialog_suffix}"
    new_description = st.text_area(
        "Description",
        value=current_description,
        key=input_key,
        height=180,
    )

    action_cols = st.columns([2, 2, 6], gap="small", vertical_alignment="center")
    with action_cols[0]:
        if st.button(
            "Save",
            key=f"scenario_list_edit_description_save_{dialog_suffix}",
            icon=":material/save:",
            type="secondary",
            use_container_width=True,
        ):
            _update_scenario_description(scenario_id, new_description)
    with action_cols[1]:
        if st.button(
            "Cancel",
            key=f"scenario_list_edit_description_cancel_{dialog_suffix}",
            use_container_width=True,
        ):
            st.rerun()


def _open_scenario_editor_for_creation():
    st.session_state[SELECTED_SCENARIO_ID_KEY] = None
    _set_editor_draft(_new_scenario_draft(), "create")
    st.switch_page(SCENARIO_EDITOR_PAGE_PATH)


def _open_scenario_editor_for_edit(scenario_id: str):
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


def _scenario_execution_header(execution_payload: dict) -> str:
    scenario_name = str(
        execution_payload.get("scenario_description")
        or execution_payload.get("scenario_code")
        or "Scenario"
    ).strip()
    status = _execution_status_label(str(execution_payload.get("status") or ""))
    timestamp = _format_datetime(execution_payload.get("started_at"))
    return f"{scenario_name} | {status} | {timestamp}"


def _render_execution_step_details(step_execution: dict):
    step_code = str(step_execution.get("step_code") or "").strip()
    step_description = str(step_execution.get("step_description") or "").strip()
    step_label = (
        f"{step_description} [{step_code}]"
        if step_description and step_code and step_description != step_code
        else (step_description or step_code or "Step")
    )
    step_status = _execution_status_label(str(step_execution.get("status") or ""))
    step_time = _format_datetime(step_execution.get("started_at"))
    st.markdown(f"- **{step_label}** | {step_status} | {step_time}")
    step_error_message = str(step_execution.get("error_message") or "").strip()
    if step_error_message:
        st.caption(f"Error: {step_error_message}")

    operation_executions = step_execution.get("operations") or []
    if not isinstance(operation_executions, list) or not operation_executions:
        return
    for operation_execution in operation_executions:
        operation_code = str(operation_execution.get("operation_code") or "").strip()
        operation_description = str(operation_execution.get("operation_description") or "").strip()
        operation_label = (
            f"{operation_description} [{operation_code}]"
            if operation_description
            and operation_code
            and operation_description != operation_code
            else (operation_description or operation_code or "Operation")
        )
        operation_status = _execution_status_label(str(operation_execution.get("status") or ""))
        operation_time = _format_datetime(operation_execution.get("started_at"))
        st.caption(f"  - {operation_label} | {operation_status} | {operation_time}")
        operation_error_message = str(operation_execution.get("error_message") or "").strip()
        if operation_error_message:
            st.caption(f"    Error: {operation_error_message}")


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

    execution_id = str(st.session_state.get(SCENARIO_LAST_EXECUTION_ID_KEY) or "").strip()
    if not execution_id:
        return {}
    live_state = get_execution_state(execution_id)
    if not isinstance(live_state, dict):
        return {}
    if str(live_state.get("scenario_id") or "").strip() != scenario_id:
        return {}
    return live_state


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
            _open_scenario_editor_for_creation()

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
            row_cols = st.columns([7, 1, 1, 1, 1], gap="small", vertical_alignment="center")
            with row_cols[0]:
                st.write(label)
            with row_cols[1]:
                if st.button(
                    "",
                    key=f"execute_scenario_list_btn_{scenario_id or idx}",
                    icon=":material/play_arrow:",
                    help="Avvia scenario",
                    use_container_width=True,
                ):
                    _execute_scenario(scenario_id)
            with row_cols[2]:
                if st.button(
                    "",
                    key=f"edit_scenario_description_list_btn_{scenario_id or idx}",
                    icon=":material/edit:",
                    help="Modifica descrizione",
                    use_container_width=True,
                ):
                    _edit_scenario_description_list_dialog(
                        scenario_id=scenario_id,
                        current_description=str(scenario.get("description") or ""),
                        dialog_suffix=f"{scenario_id or idx}",
                    )
            with row_cols[3]:
                if st.button(
                    "",
                    key=f"edit_scenario_list_btn_{scenario_id or idx}",
                    icon=":material/settings:",
                    help="Modifica scenario",
                    use_container_width=True,
                ):
                    _open_scenario_editor_for_edit(scenario_id)
            with row_cols[4]:
                if st.button(
                    "",
                    key=f"delete_scenario_list_btn_{scenario_id or idx}",
                    icon=":material/delete:",
                    help="Elimina scenario",
                    use_container_width=True,
                ):
                    _delete_scenario(scenario_id)

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
            _open_scenario_editor_for_creation()
        _render_feedback()
        return

    scenario = st.session_state.get(SCENARIO_DRAFT_KEY)
    description = str(scenario.get("description") or "").strip() or "-"
    st.title(description)

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
        header = _scenario_execution_header(execution_payload)

        with st.expander(header, expanded=False):
            action_cols = st.columns([1, 5], gap="small", vertical_alignment="center")
            with action_cols[0]:
                if st.button(
                    "",
                    key=f"home_open_scenario_editor_{execution_id or idx}",
                    icon=":material/open_in_new:",
                    help="Apri scenario editor",
                    use_container_width=True,
                    disabled=not bool(scenario_id),
                ):
                    _open_scenario_editor_for_edit(scenario_id)
            with action_cols[1]:
                st.caption(f"Execution id: {execution_id or '-'}")

            global_error = str(execution_payload.get("error_message") or "").strip()
            if global_error:
                st.caption(f"Error: {global_error}")

            step_executions = execution_payload.get("steps") or []
            if not isinstance(step_executions, list) or not step_executions:
                st.caption("Nessun dettaglio step.")
                continue
            for step_execution in step_executions:
                if isinstance(step_execution, dict):
                    _render_execution_step_details(step_execution)


def render_scenarios_page():
    render_scenarios_list_page()
