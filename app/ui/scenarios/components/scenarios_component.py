from copy import deepcopy
from decimal import Decimal
from uuid import uuid4

import streamlit as st

from scenarios.components.scenario_operation_component import (
    render_add_new_step_operation_dialog as operation_render_add_new_dialog,
    render_import_step_operation_dialog as operation_render_import_dialog,
    render_operation_component as operation_render_component,
)
from steps.step_component import (
    render_add_new_scenario_step_dialog as step_render_add_new_dialog,
    render_import_scenario_step_dialog as step_render_import_dialog,
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
    get_scenario_by_id,
    update_scenario,
)
from scenarios.services.state_keys import (
    ADD_SCENARIO_STEP_DIALOG_CREATE_NEW_KEY,
    ADD_SCENARIO_STEP_DIALOG_NONCE_KEY,
    ADD_SCENARIO_STEP_DIALOG_OPEN_KEY,
    ADD_STEP_OPERATION_DIALOG_CREATE_NEW_KEY,
    ADD_STEP_OPERATION_DIALOG_NONCE_KEY,
    ADD_STEP_OPERATION_DIALOG_OPEN_KEY,
    ADD_STEP_OPERATION_DIALOG_TARGET_STEP_UI_KEY,
    ON_FAILURE_OPTIONS,
    OPERATIONS_CATALOG_KEY,
    PENDING_SCENARIO_SWITCH_KEY,
    SCENARIOS_KEY,
    SCENARIO_BASELINE_PAYLOAD_KEY,
    SCENARIO_DRAFT_KEY,
    SCENARIO_EDITOR_MODE_KEY,
    SCENARIO_EDITOR_NONCE_KEY,
    SCENARIO_FEEDBACK_KEY,
    SELECTED_SCENARIO_ID_KEY,
    STEPS_CATALOG_KEY,
)

SCENARIOS_LIST_PAGE_PATH = "pages/Scenarios.py"
SCENARIO_EDITOR_PAGE_PATH = "pages/ScenarioEditor.py"


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


def _clear_pending_switch():
    st.session_state.pop(PENDING_SCENARIO_SWITCH_KEY, None)


def _bump_editor_nonce():
    st.session_state[SCENARIO_EDITOR_NONCE_KEY] = (
        int(st.session_state.get(SCENARIO_EDITOR_NONCE_KEY, 0)) + 1
    )


def _set_editor_draft(draft: dict | None, mode: str, reset_baseline: bool = True):
    st.session_state[SCENARIO_DRAFT_KEY] = draft
    st.session_state[SCENARIO_EDITOR_MODE_KEY] = mode
    _close_add_scenario_step_dialog()
    _close_add_step_operation_dialog()
    if reset_baseline:
        _set_baseline_payload_from_draft(draft)
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


def _open_add_scenario_step_dialog(create_new: bool):
    _close_add_step_operation_dialog()
    st.session_state[ADD_SCENARIO_STEP_DIALOG_OPEN_KEY] = True
    st.session_state[ADD_SCENARIO_STEP_DIALOG_CREATE_NEW_KEY] = create_new
    st.session_state[ADD_SCENARIO_STEP_DIALOG_NONCE_KEY] = (
        int(st.session_state.get(ADD_SCENARIO_STEP_DIALOG_NONCE_KEY, 0)) + 1
    )


def _open_add_new_scenario_step_dialog():
    _open_add_scenario_step_dialog(create_new=True)


def _open_import_scenario_step_dialog():
    _open_add_scenario_step_dialog(create_new=False)


def _close_add_scenario_step_dialog():
    st.session_state[ADD_SCENARIO_STEP_DIALOG_OPEN_KEY] = False
    st.session_state.pop(ADD_SCENARIO_STEP_DIALOG_CREATE_NEW_KEY, None)


def _open_add_step_operation_dialog(step_ui_key: str, create_new: bool):
    if not step_ui_key:
        return
    _close_add_scenario_step_dialog()
    st.session_state[ADD_STEP_OPERATION_DIALOG_OPEN_KEY] = True
    st.session_state[ADD_STEP_OPERATION_DIALOG_CREATE_NEW_KEY] = create_new
    st.session_state[ADD_STEP_OPERATION_DIALOG_TARGET_STEP_UI_KEY] = step_ui_key
    st.session_state[ADD_STEP_OPERATION_DIALOG_NONCE_KEY] = (
        int(st.session_state.get(ADD_STEP_OPERATION_DIALOG_NONCE_KEY, 0)) + 1
    )


def _open_add_new_step_operation_dialog(step_ui_key: str):
    _open_add_step_operation_dialog(step_ui_key, create_new=True)


def _open_import_step_operation_dialog(step_ui_key: str):
    _open_add_step_operation_dialog(step_ui_key, create_new=False)


def _close_add_step_operation_dialog():
    st.session_state[ADD_STEP_OPERATION_DIALOG_OPEN_KEY] = False
    st.session_state.pop(ADD_STEP_OPERATION_DIALOG_CREATE_NEW_KEY, None)
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
            draft_operations.append(
                {
                    "id": step_operation.get("id"),
                    "order": _safe_int(step_operation.get("order"), op_idx + 1),
                    "operation_id": str(step_operation.get("operation_id") or ""),
                    "_ui_key": _new_ui_key(),
                }
            )

        draft_steps.append(
            {
                "id": scenario_step.get("id"),
                "order": _safe_int(scenario_step.get("order"), step_idx + 1),
                "step_id": str(scenario_step.get("step_id") or ""),
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
                    "operation_id": str(operation.get("operation_id") or "").strip(),
                }
            )

        steps_payload.append(
            {
                "order": _safe_int(step.get("order"), 0),
                "step_id": str(step.get("step_id") or "").strip(),
                "on_failure": str(step.get("on_failure") or "ABORT"),
                "operations": operations_payload,
            }
        )

    return {
        "code": str(draft.get("code") or "").strip(),
        "description": str(draft.get("description") or ""),
        "steps": steps_payload,
    }


def _set_baseline_payload_from_draft(draft: dict | None):
    if not isinstance(draft, dict):
        st.session_state[SCENARIO_BASELINE_PAYLOAD_KEY] = None
        return
    st.session_state[SCENARIO_BASELINE_PAYLOAD_KEY] = deepcopy(
        _build_scenario_payload(draft)
    )


def _is_editor_dirty() -> bool:
    draft = st.session_state.get(SCENARIO_DRAFT_KEY)
    if not isinstance(draft, dict):
        return False

    current_payload = _build_scenario_payload(draft)
    baseline_payload = st.session_state.get(SCENARIO_BASELINE_PAYLOAD_KEY)
    if baseline_payload is None:
        return bool(
            current_payload.get("code")
            or current_payload.get("description")
            or current_payload.get("steps")
        )
    return current_payload != baseline_payload


def _validate_draft(draft: dict) -> str | None:
    payload = _build_scenario_payload(draft)
    if not payload["code"]:
        return "Il campo Code e' obbligatorio."

    for idx, step in enumerate(payload["steps"]):
        if not step["step_id"]:
            return f"Scenario step #{idx + 1}: step_id obbligatorio."
        if step["on_failure"] not in ON_FAILURE_OPTIONS:
            return (
                f"Scenario step #{idx + 1}: on_failure deve essere uno tra "
                f"{', '.join(ON_FAILURE_OPTIONS)}."
            )
        for op_idx, operation in enumerate(step["operations"]):
            if not operation["operation_id"]:
                return (
                    f"Scenario step #{idx + 1}, operation #{op_idx + 1}: "
                    "operation_id obbligatorio."
                )
    return None


def _save_draft():
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
    st.session_state[SCENARIO_FEEDBACK_KEY] = feedback
    st.rerun()


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
    try:
        execute_scenario_by_id(scenario_id)
    except Exception as exc:
        st.error(f"Errore esecuzione scenario: {str(exc)}")
        return

    st.session_state[SCENARIO_FEEDBACK_KEY] = "Scenario avviato."
    st.rerun()


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


def _undo_changes():
    mode = str(st.session_state.get(SCENARIO_EDITOR_MODE_KEY, "edit"))
    if mode == "create":
        _set_editor_draft(_new_scenario_draft(), "create")
        st.session_state[SCENARIO_FEEDBACK_KEY] = "Modifiche annullate."
        st.rerun()

    selected_id = str(st.session_state.get(SELECTED_SCENARIO_ID_KEY) or "")
    if not selected_id:
        _set_editor_draft(None, "edit")
        st.session_state[SCENARIO_FEEDBACK_KEY] = "Modifiche annullate."
        st.rerun()

    restored = _build_scenario_draft(selected_id)
    if restored is None:
        st.error("Errore durante l'annullamento modifiche.")
        return

    _set_editor_draft(restored, "edit")
    st.session_state[SCENARIO_FEEDBACK_KEY] = "Modifiche annullate."
    st.rerun()


def _render_operation_component(
    scenario_step: dict,
    operation: dict,
    op_idx: int,
    step_ui_key: str,
    nonce: int,
    operation_catalog: list[dict],
    operation_labels_by_id: dict[str, str],
):
    operation_render_component(
        scenario_step,
        operation,
        op_idx,
        step_ui_key,
        nonce,
        operation_catalog,
        operation_labels_by_id,
    )


def _render_step_component(
    draft: dict,
    scenario_step: dict,
    step_idx: int,
    nonce: int,
    step_catalog: list[dict],
    operation_catalog: list[dict],
    step_labels_by_id: dict[str, str],
    operation_labels_by_id: dict[str, str],
):
    step_render_component(
        draft,
        scenario_step,
        step_idx,
        nonce,
        step_catalog,
        operation_catalog,
        step_labels_by_id,
        operation_labels_by_id,
        ON_FAILURE_OPTIONS,
        _render_operation_component,
        _open_add_new_step_operation_dialog,
        _open_import_step_operation_dialog,
    )


def _render_import_scenario_step_dialog(
    draft: dict,
    step_catalog: list[dict],
    step_labels_by_id: dict[str, str],
):
    step_render_import_dialog(
        draft,
        step_catalog,
        step_labels_by_id,
        _close_add_scenario_step_dialog,
    )


def _render_add_new_scenario_step_dialog(draft: dict):
    step_render_add_new_dialog(draft, _close_add_scenario_step_dialog)


@st.dialog("Import step", width="large")
def _import_scenario_step_dialog(
    draft: dict,
    step_catalog: list[dict],
    step_labels_by_id: dict[str, str],
):
    _render_import_scenario_step_dialog(draft, step_catalog, step_labels_by_id)


@st.dialog("Add new step", width="large")
def _add_new_scenario_step_dialog(draft: dict):
    _render_add_new_scenario_step_dialog(draft)


def _render_import_step_operation_dialog(
    draft: dict,
    operation_catalog: list[dict],
    operation_labels_by_id: dict[str, str],
):
    operation_render_import_dialog(
        draft,
        operation_catalog,
        operation_labels_by_id,
        _close_add_step_operation_dialog,
    )


def _render_add_new_step_operation_dialog(draft: dict):
    operation_render_add_new_dialog(draft, _close_add_step_operation_dialog)


@st.dialog("Import operation", width="large")
def _import_step_operation_dialog(
    draft: dict,
    operation_catalog: list[dict],
    operation_labels_by_id: dict[str, str],
):
    _render_import_step_operation_dialog(draft, operation_catalog, operation_labels_by_id)


@st.dialog("Add new operation", width="large")
def _add_new_step_operation_dialog(draft: dict):
    _render_add_new_step_operation_dialog(draft)


def _render_editor():
    draft = st.session_state.get(SCENARIO_DRAFT_KEY)
    if not isinstance(draft, dict):
        return

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
            operation_catalog,
            step_labels_by_id,
            operation_labels_by_id,
        )

    if st.session_state.get(ADD_SCENARIO_STEP_DIALOG_OPEN_KEY, False):
        create_new = bool(st.session_state.get(ADD_SCENARIO_STEP_DIALOG_CREATE_NEW_KEY, False))
        if create_new:
            _add_new_scenario_step_dialog(draft)
        else:
            _import_scenario_step_dialog(draft, step_catalog, step_labels_by_id)
    if st.session_state.get(ADD_STEP_OPERATION_DIALOG_OPEN_KEY, False):
        create_new = bool(st.session_state.get(ADD_STEP_OPERATION_DIALOG_CREATE_NEW_KEY, False))
        if create_new:
            _add_new_step_operation_dialog(draft)
        else:
            _import_step_operation_dialog(draft, operation_catalog, operation_labels_by_id)


def _render_step_toolbar():

    nonce = int(st.session_state.get(SCENARIO_EDITOR_NONCE_KEY, 0))
    action_cols = st.columns([8, 2, 2, 2, 2], gap="small", vertical_alignment="bottom")
    if _is_editor_dirty():  
        with action_cols[1]:
            if st.button(
                "Save",
                key="save_scenario_btn",
                icon=":material/save:",
                type="secondary",
                use_container_width=True,
            ):
                _save_draft()

        with action_cols[2]:
            if st.button(
                "Undo",
                key="undo_scenario_btn",
                icon=":material/undo:",
                type="secondary",
                use_container_width=True,
            ):
                _undo_changes()

    with action_cols[3]:
        if st.button(
            "",
            help="Crea un nuovo step e aggiungilo allo scenario.",
            key=f"scenario_{nonce}_add_new_step",
            icon=":material/add:",
            use_container_width=True
        ):
            _open_add_new_scenario_step_dialog()
            st.rerun()

    with action_cols[4]:
        if st.button(
            "",
            help="Importa uno step esistente e aggiungilo allo scenario.",
            key=f"scenario_{nonce}_import_step",
            icon=":material/download:",
            use_container_width=True
        ):
            _open_import_scenario_step_dialog()
            st.rerun()

    

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


def _render_editor_main_fields():
    draft = st.session_state.get(SCENARIO_DRAFT_KEY)
    if not isinstance(draft, dict):
        return

    mode = str(st.session_state.get(SCENARIO_EDITOR_MODE_KEY, "edit"))
    nonce = int(st.session_state.get(SCENARIO_EDITOR_NONCE_KEY, 0))
    scenario_id = str(draft.get("id") or "")
    is_existing_scenario = mode == "edit" and bool(scenario_id)

    if is_existing_scenario:
        description = str(draft.get("description") or "").strip() or "-"
        st.title(description)
        return

    draft["code"] = st.text_input(
        "Code",
        value=str(draft.get("code") or ""),
        key=f"scenario_{nonce}_code",
    ).strip()
    draft["description"] = st.text_input(
        "Description",
        value=str(draft.get("description") or ""),
        key=f"scenario_{nonce}_description",
    )
    if mode == "create":
        st.caption("Scenario in creazione.")

def _render_feedback():
    feedback_message = st.session_state.pop(SCENARIO_FEEDBACK_KEY, None)
    if feedback_message:
        st.success(feedback_message, icon=":material/check_circle:")


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

    _render_editor_main_fields()
    st.divider()
    _render_editor()
    st.divider()
    _render_step_toolbar()
    _render_feedback()


def render_scenarios_page():
    render_scenarios_list_page()
