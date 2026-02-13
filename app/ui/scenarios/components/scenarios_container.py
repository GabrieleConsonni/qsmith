import json
from copy import deepcopy
from decimal import Decimal
from uuid import uuid4

import streamlit as st

from scenarios.services.data_loader_service import (
    load_operations_catalog,
    load_scenarios_context,
    load_steps_catalog,
)
from scenarios.services.scenario_api_service import (
    create_operation,
    create_step,
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


def _step_type_label(step_type: str) -> str:
    labels = {
        STEP_TYPE_SLEEP: "sleep",
        STEP_TYPE_DATA: "data",
        STEP_TYPE_DATA_FROM_JSON_ARRAY: "data-from-json-array",
        STEP_TYPE_DATA_FROM_DB: "data-from-db",
        STEP_TYPE_DATA_FROM_QUEUE: "data-from-queue",
    }
    return labels.get(step_type, step_type or "-")


def _operation_type_label(operation_type: str) -> str:
    labels = {
        OPERATION_TYPE_PUBLISH: "publish",
        OPERATION_TYPE_SAVE_INTERNAL_DB: "save-internal-db",
        OPERATION_TYPE_SAVE_EXTERNAL_DB: "save-external-db",
    }
    return labels.get(operation_type, operation_type or "-")


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


def _parse_json_object(value: str) -> tuple[dict | None, str | None]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        return None, f"JSON non valido: {str(exc)}"
    if not isinstance(parsed, dict):
        return None, "Il valore deve essere un oggetto JSON."
    return parsed, None


def _open_add_scenario_step_dialog():
    _close_add_step_operation_dialog()
    st.session_state[ADD_SCENARIO_STEP_DIALOG_OPEN_KEY] = True
    st.session_state[ADD_SCENARIO_STEP_DIALOG_CREATE_NEW_KEY] = False
    st.session_state[ADD_SCENARIO_STEP_DIALOG_NONCE_KEY] = (
        int(st.session_state.get(ADD_SCENARIO_STEP_DIALOG_NONCE_KEY, 0)) + 1
    )


def _close_add_scenario_step_dialog():
    st.session_state[ADD_SCENARIO_STEP_DIALOG_OPEN_KEY] = False
    st.session_state.pop(ADD_SCENARIO_STEP_DIALOG_CREATE_NEW_KEY, None)


def _open_add_step_operation_dialog(step_ui_key: str):
    if not step_ui_key:
        return
    _close_add_scenario_step_dialog()
    st.session_state[ADD_STEP_OPERATION_DIALOG_OPEN_KEY] = True
    st.session_state[ADD_STEP_OPERATION_DIALOG_CREATE_NEW_KEY] = False
    st.session_state[ADD_STEP_OPERATION_DIALOG_TARGET_STEP_UI_KEY] = step_ui_key
    st.session_state[ADD_STEP_OPERATION_DIALOG_NONCE_KEY] = (
        int(st.session_state.get(ADD_STEP_OPERATION_DIALOG_NONCE_KEY, 0)) + 1
    )


def _close_add_step_operation_dialog():
    st.session_state[ADD_STEP_OPERATION_DIALOG_OPEN_KEY] = False
    st.session_state.pop(ADD_STEP_OPERATION_DIALOG_CREATE_NEW_KEY, None)
    st.session_state.pop(ADD_STEP_OPERATION_DIALOG_TARGET_STEP_UI_KEY, None)


def _new_draft_operation(
    default_operation_id: str = "",
    order: int = 1,
    edit_mode: bool = True,
) -> dict:
    return {
        "id": None,
        "order": order,
        "operation_id": default_operation_id,
        "_ui_key": _new_ui_key(),
        "_edit_mode": edit_mode,
    }


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
                    "_edit_mode": False,
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


def _start_create_mode():
    st.session_state[SELECTED_SCENARIO_ID_KEY] = None
    _set_editor_draft(_new_scenario_draft(), "create")
    st.rerun()


def _select_scenario(scenario_id: str):
    st.session_state[SELECTED_SCENARIO_ID_KEY] = scenario_id
    _set_editor_draft(_build_scenario_draft(scenario_id), "edit")
    st.rerun()


def _request_create_mode():
    if _is_editor_dirty():
        st.session_state[PENDING_SCENARIO_SWITCH_KEY] = {
            "target_mode": "create",
            "scenario_id": None,
        }
        st.rerun()
    _start_create_mode()


def _request_select_scenario(scenario_id: str):
    current_mode = str(st.session_state.get(SCENARIO_EDITOR_MODE_KEY, "edit"))
    current_selected_id = str(st.session_state.get(SELECTED_SCENARIO_ID_KEY) or "")
    if current_mode == "edit" and current_selected_id == str(scenario_id):
        return

    if _is_editor_dirty():
        st.session_state[PENDING_SCENARIO_SWITCH_KEY] = {
            "target_mode": "edit",
            "scenario_id": str(scenario_id),
        }
        st.rerun()
    _select_scenario(scenario_id)


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


def _render_pending_switch_warning():
    pending_switch = st.session_state.get(PENDING_SCENARIO_SWITCH_KEY)
    if not isinstance(pending_switch, dict):
        return

    target_mode = str(pending_switch.get("target_mode") or "edit")
    scenario_id = str(pending_switch.get("scenario_id") or "")
    target_label = "creazione nuovo scenario"
    if target_mode == "edit" and scenario_id:
        scenarios = st.session_state.get(SCENARIOS_KEY, [])
        target_scenario = next(
            (
                item
                for item in scenarios
                if isinstance(item, dict) and str(item.get("id")) == scenario_id
            ),
            None,
        )
        target_code = (
            str(target_scenario.get("code"))
            if isinstance(target_scenario, dict) and target_scenario.get("code")
            else scenario_id
        )
        target_label = f"scenario '{target_code}'"

    st.warning(
        "Hai modifiche non salvate. "
        f"Per spostarti su {target_label} devi prima salvarle o annullarle."
    )
    action_cols = st.columns([2, 2, 6], gap="small", vertical_alignment="center")
    with action_cols[0]:
        if st.button(
            "Discard",
            key="pending_switch_discard_btn",
            icon=":material/undo:",
            type="secondary",
            use_container_width=True,
        ):
            _clear_pending_switch()
            if target_mode == "create":
                _start_create_mode()
            elif scenario_id:
                _select_scenario(scenario_id)
            st.rerun()
    with action_cols[1]:
        if st.button(
            "Cancel",
            key="pending_switch_cancel_btn",
            type="secondary",
            use_container_width=True,
        ):
            _clear_pending_switch()
            st.rerun()


def _render_left_scenarios_list(scenarios: list[dict]):
    selected_id = st.session_state.get(SELECTED_SCENARIO_ID_KEY)
    mode = str(st.session_state.get(SCENARIO_EDITOR_MODE_KEY, "edit"))

    if not scenarios:
        return

    for idx, scenario in enumerate(scenarios):
        scenario_id = str(scenario.get("id") or "")
        code = scenario.get("code") or "-"
        description = scenario.get("description") or code
        is_selected = mode != "create" and str(selected_id) == scenario_id
        with st.container(border=True):
            row_cols = st.columns([6, 1, 1], gap="small", vertical_alignment="center")
            with row_cols[0]:
                if st.button(
                    description,
                    key=f"select_scenario_btn_{scenario_id or idx}",
                    type="primary" if is_selected else "secondary",
                    use_container_width=True,
                    help="Select scenario",
                ):
                    _request_select_scenario(scenario_id)
            with row_cols[1]:
                if st.button(
                    "",
                    key=f"execute_scenario_btn_{scenario_id or idx}",
                    icon=":material/play_arrow:",
                    help="Execute scenario",
                    use_container_width=True,
                ):
                    _execute_scenario(scenario_id)
            with row_cols[2]:
                if st.button(
                    "",
                    key=f"delete_scenario_btn_{scenario_id or idx}",
                    icon=":material/delete:",
                    help="Delete scenario",
                    use_container_width=True,
                ):
                    _delete_scenario(scenario_id)


def _render_operation_container(
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
    operation_edit_mode = bool(operation.get("_edit_mode", False))

    with st.container(border=True):
        if operation_edit_mode:
            operation["order"] = int(
                st.number_input(
                    "Operation order",
                    min_value=0,
                    value=_safe_int(operation.get("order"), op_idx + 1),
                    key=f"scenario_{nonce}_step_{step_ui_key}_operation_order_{operation_ui_key}",
                )
            )
            if operation_catalog:
                operation_options = [
                    str(item.get("id")) for item in operation_catalog if item.get("id")
                ]
                if operation_options:
                    current_operation_id = str(operation.get("operation_id") or "")
                    if (
                        current_operation_id
                        and current_operation_id not in operation_options
                    ):
                        operation_options.insert(0, current_operation_id)
                    selected_operation_id = st.selectbox(
                        "Operation",
                        options=operation_options,
                        index=(
                            operation_options.index(current_operation_id)
                            if current_operation_id in operation_options
                            else 0
                        ),
                        format_func=lambda _id: operation_labels_by_id.get(
                            _id, f"Unknown ({_id})"
                        ),
                        key=f"scenario_{nonce}_step_{step_ui_key}_operation_select_{operation_ui_key}",
                    )
                    operation["operation_id"] = str(selected_operation_id)
                else:
                    operation["operation_id"] = st.text_input(
                        "Operation id",
                        value=str(operation.get("operation_id") or ""),
                        key=f"scenario_{nonce}_step_{step_ui_key}_operation_input_{operation_ui_key}",
                    ).strip()
            else:
                operation["operation_id"] = st.text_input(
                    "Operation id",
                    value=str(operation.get("operation_id") or ""),
                    key=f"scenario_{nonce}_step_{step_ui_key}_operation_input_{operation_ui_key}",
                ).strip()
        else:
            operation_order = _safe_int(operation.get("order"), op_idx + 1)
            operation_id = str(operation.get("operation_id") or "")
            operation_label = operation_labels_by_id.get(
                operation_id, f"Unknown ({operation_id})"
            )
            st.write(f"Operation #{operation_order}: {operation_label}")

        operation_action_cols = st.columns([8, 1, 1], gap="small", vertical_alignment="center")
        with operation_action_cols[1]:
            icon = ":material/save:" if operation_edit_mode else ":material/edit:"
            if st.button(
                "",
                key=f"scenario_{nonce}_step_{step_ui_key}_operation_edit_toggle_{operation_ui_key}",
                icon=icon,
                help="Save operation" if operation_edit_mode else "Modify operation",
                use_container_width=True,
            ):
                operation["_edit_mode"] = not operation_edit_mode
                st.rerun()
        with operation_action_cols[2]:
            if st.button(
                "",
                key=f"scenario_{nonce}_step_{step_ui_key}_operation_delete_{operation_ui_key}",
                icon=":material/delete:",
                help="Delete operation",
            ):
                scenario_step.get("operations", []).pop(op_idx)
                st.rerun()


def _render_step_container(
    draft: dict,
    scenario_step: dict,
    step_idx: int,
    nonce: int,
    step_catalog: list[dict],
    operation_catalog: list[dict],
    step_labels_by_id: dict[str, str],
    operation_labels_by_id: dict[str, str],
):
    step_ui_key = scenario_step.get("_ui_key") or f"step_{step_idx}"
    scenario_step["_ui_key"] = step_ui_key
    step_edit_mode = bool(scenario_step.get("_edit_mode", False))
    step_order = _safe_int(scenario_step.get("order"), step_idx + 1)
    step_id = str(scenario_step.get("step_id") or "")
    step_label = step_labels_by_id.get(step_id, f"Unknown ({step_id})")

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
                options=ON_FAILURE_OPTIONS,
                index=(
                    ON_FAILURE_OPTIONS.index(on_failure)
                    if on_failure in ON_FAILURE_OPTIONS
                    else 0
                ),
                key=f"scenario_{nonce}_step_on_failure_{step_ui_key}",
            )
        else:
            st.caption(f"on_failure: {scenario_step.get('on_failure') or 'ABORT'}")

        st.markdown("**Step operations**")
        operations = scenario_step.get("operations") or []

        for op_idx, operation in enumerate(operations):
            _render_operation_container(
                scenario_step,
                operation,
                op_idx,
                step_ui_key,
                nonce,
                operation_catalog,
                operation_labels_by_id,
            )

        if st.button(
            "Add operation",
            key=f"scenario_{nonce}_step_add_operation_{step_ui_key}",
            icon=":material/add:",
            use_container_width=True,
        ):
            _open_add_step_operation_dialog(step_ui_key)
            st.rerun()

        step_action_cols = st.columns([8, 1, 1], gap="small", vertical_alignment="center")
        with step_action_cols[1]:
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
        with step_action_cols[2]:
            if st.button(
                "",
                key=f"scenario_{nonce}_step_delete_{step_ui_key}",
                icon=":material/delete:",
                help="Delete scenario step",
                use_container_width=True,
            ):
                draft.get("steps", []).pop(step_idx)
                st.rerun()


def _find_draft_step_by_ui_key(draft: dict, step_ui_key: str) -> dict | None:
    if not step_ui_key:
        return None
    for scenario_step in draft.get("steps") or []:
        if str(scenario_step.get("_ui_key") or "") == str(step_ui_key):
            return scenario_step
    return None


def _append_operation_to_step(scenario_step: dict, operation_id: str):
    operation_id_value = str(operation_id or "").strip()
    if not operation_id_value:
        return
    operations = scenario_step.setdefault("operations", [])
    operations.append(
        _new_draft_operation(
            default_operation_id=operation_id_value,
            order=len(operations) + 1,
            edit_mode=False,
        )
    )


def _append_step_to_draft(draft: dict, step_id: str):
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


def _build_step_creation_payload(dialog_nonce: int) -> tuple[dict | None, str | None]:
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
        connection_id = str(
            st.session_state.get(f"scenario_add_step_connection_id_{dialog_nonce}") or ""
        ).strip()
        table_name = str(
            st.session_state.get(f"scenario_add_step_table_name_{dialog_nonce}") or ""
        ).strip()
        query = str(st.session_state.get(f"scenario_add_step_query_{dialog_nonce}") or "").strip()
        order_by_raw = str(
            st.session_state.get(f"scenario_add_step_order_by_{dialog_nonce}") or ""
        )
        order_by_values = [item.strip() for item in order_by_raw.split(",") if item.strip()]
        stream = bool(
            st.session_state.get(f"scenario_add_step_stream_{dialog_nonce}", True)
        )
        chunk_size = _safe_int(
            st.session_state.get(f"scenario_add_step_chunk_size_{dialog_nonce}"), 100
        )
        if not connection_id:
            return None, "Il campo Connection id e' obbligatorio."
        if not table_name:
            return None, "Il campo Table name e' obbligatorio."
        if chunk_size <= 0:
            return None, "Il campo Chunk size deve essere maggiore di zero."
        cfg = {
            "stepType": STEP_TYPE_DATA_FROM_DB,
            "connection_id": connection_id,
            "table_name": table_name,
            "query": query or None,
            "order_by": order_by_values or None,
            "stream": stream,
            "chunk_size": chunk_size,
        }
    elif step_type == STEP_TYPE_DATA_FROM_QUEUE:
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


def _render_readonly_step_preview(selected_step: dict, dialog_nonce: int):
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


@st.dialog("Add scenario step", width="large")
def _add_scenario_step_dialog(draft: dict, step_catalog: list[dict], step_labels_by_id: dict[str, str]):
    dialog_nonce = int(st.session_state.get(ADD_SCENARIO_STEP_DIALOG_NONCE_KEY, 0))
    create_new = bool(st.session_state.get(ADD_SCENARIO_STEP_DIALOG_CREATE_NEW_KEY, False))
    step_ids = [str(item.get("id")) for item in step_catalog if item.get("id")]
    step_by_id = {str(item.get("id")): item for item in step_catalog if item.get("id")}

    selection_cols = st.columns([8, 1], gap="small", vertical_alignment="bottom")
    selected_step_id = ""
    with selection_cols[0]:
        if step_ids:
            selected_step_id = st.selectbox(
                "Existing step",
                options=step_ids,
                format_func=lambda _id: step_labels_by_id.get(_id, f"Unknown ({_id})"),
                key=f"scenario_add_step_existing_select_{dialog_nonce}",
                disabled=create_new,
            )
    with selection_cols[1]:
        if create_new:
            if st.button(
                "",
                key=f"scenario_add_step_use_existing_{dialog_nonce}",
                icon=":material/list:",
                help="Use existing step",
                use_container_width=True,
                disabled=not bool(step_ids),
            ):
                st.session_state[ADD_SCENARIO_STEP_DIALOG_CREATE_NEW_KEY] = False
                st.rerun()
        else:
            if st.button(
                "",
                key=f"scenario_add_step_create_new_{dialog_nonce}",
                icon=":material/add:",
                help="Create new step",
                use_container_width=True,
            ):
                st.session_state[ADD_SCENARIO_STEP_DIALOG_CREATE_NEW_KEY] = True
                st.rerun()

    if not create_new:
        _render_readonly_step_preview(step_by_id.get(selected_step_id), dialog_nonce)
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
                _append_step_to_draft(draft, selected_step_id)
                _close_add_scenario_step_dialog()
                st.session_state[SCENARIO_FEEDBACK_KEY] = "Scenario step aggiunto."
                st.rerun()
        with action_cols[2]:
            if st.button(
                "Cancel",
                key=f"scenario_add_step_cancel_existing_{dialog_nonce}",
                use_container_width=True,
            ):
                _close_add_scenario_step_dialog()
                st.rerun()
        return

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
    elif step_type == STEP_TYPE_DATA_FROM_JSON_ARRAY:
        st.text_input(
            "Json array id",
            key=f"scenario_add_step_json_array_id_{dialog_nonce}",
        )
    elif step_type == STEP_TYPE_DATA_FROM_DB:
        st.text_input(
            "Connection id",
            key=f"scenario_add_step_connection_id_{dialog_nonce}",
        )
        st.text_input(
            "Table name",
            key=f"scenario_add_step_table_name_{dialog_nonce}",
        )
        st.text_input(
            "Query (optional)",
            key=f"scenario_add_step_query_{dialog_nonce}",
        )
        st.text_input(
            "Order by (comma separated, optional)",
            key=f"scenario_add_step_order_by_{dialog_nonce}",
        )
        st.checkbox(
            "Stream",
            key=f"scenario_add_step_stream_{dialog_nonce}",
            value=True,
        )
        st.number_input(
            "Chunk size",
            min_value=1,
            value=100,
            step=1,
            key=f"scenario_add_step_chunk_size_{dialog_nonce}",
        )
    elif step_type == STEP_TYPE_DATA_FROM_QUEUE:
        st.text_input(
            "Queue id",
            key=f"scenario_add_step_queue_id_{dialog_nonce}",
        )
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
            payload, validation_error = _build_step_creation_payload(dialog_nonce)
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
            _append_step_to_draft(draft, created_step_id)
            _close_add_scenario_step_dialog()
            st.session_state[SCENARIO_FEEDBACK_KEY] = "Nuovo step creato e aggiunto."
            st.rerun()
    with create_cols[2]:
        if st.button(
            "Cancel",
            key=f"scenario_add_step_cancel_new_{dialog_nonce}",
            use_container_width=True,
        ):
            _close_add_scenario_step_dialog()
            st.rerun()


def _build_operation_creation_payload(dialog_nonce: int) -> tuple[dict | None, str | None]:
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
        template_id = str(
            st.session_state.get(f"scenario_add_operation_template_id_{dialog_nonce}") or ""
        ).strip()
        template_params_raw = str(
            st.session_state.get(f"scenario_add_operation_template_params_{dialog_nonce}") or ""
        ).strip()
        if not queue_id:
            return None, "Il campo Queue id e' obbligatorio."
        template_params: dict | None = None
        if template_params_raw:
            parsed_template_params, parse_error = _parse_json_object(template_params_raw)
            if parse_error:
                return None, parse_error
            template_params = parsed_template_params

        cfg = {
            "operationType": OPERATION_TYPE_PUBLISH,
            "queue_id": queue_id,
            "template_id": template_id or None,
            "template_params": template_params or None,
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
            st.session_state.get(f"scenario_add_operation_connection_id_{dialog_nonce}")
            or ""
        ).strip()
        table_name = str(
            st.session_state.get(f"scenario_add_operation_external_table_name_{dialog_nonce}")
            or ""
        ).strip()
        if not connection_id:
            return None, "Il campo Connection id e' obbligatorio."
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


def _render_readonly_operation_preview(selected_operation: dict, dialog_nonce: int):
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


@st.dialog("Add operation", width="large")
def _add_step_operation_dialog(
    draft: dict,
    operation_catalog: list[dict],
    operation_labels_by_id: dict[str, str],
):
    dialog_nonce = int(st.session_state.get(ADD_STEP_OPERATION_DIALOG_NONCE_KEY, 0))
    create_new = bool(st.session_state.get(ADD_STEP_OPERATION_DIALOG_CREATE_NEW_KEY, False))
    target_step_ui_key = str(
        st.session_state.get(ADD_STEP_OPERATION_DIALOG_TARGET_STEP_UI_KEY) or ""
    )
    scenario_step = _find_draft_step_by_ui_key(draft, target_step_ui_key)

    if not isinstance(scenario_step, dict):
        st.error("Step di destinazione non trovato.")
        if st.button(
            "Cancel",
            key=f"scenario_add_operation_missing_step_cancel_{dialog_nonce}",
            use_container_width=True,
        ):
            _close_add_step_operation_dialog()
            st.rerun()
        return

    operation_ids = [str(item.get("id")) for item in operation_catalog if item.get("id")]
    operation_by_id = {
        str(item.get("id")): item for item in operation_catalog if item.get("id")
    }

    selection_cols = st.columns([8, 1], gap="small", vertical_alignment="bottom")
    selected_operation_id = ""
    with selection_cols[0]:
        if operation_ids:
            selected_operation_id = st.selectbox(
                "Existing operation",
                options=operation_ids,
                format_func=lambda _id: operation_labels_by_id.get(_id, f"Unknown ({_id})"),
                key=f"scenario_add_operation_existing_select_{dialog_nonce}",
                disabled=create_new,
            )
    with selection_cols[1]:
        if create_new:
            if st.button(
                "",
                key=f"scenario_add_operation_use_existing_{dialog_nonce}",
                icon=":material/list:",
                help="Use existing operation",
                use_container_width=True,
                disabled=not bool(operation_ids),
            ):
                st.session_state[ADD_STEP_OPERATION_DIALOG_CREATE_NEW_KEY] = False
                st.rerun()
        else:
            if st.button(
                "",
                key=f"scenario_add_operation_create_new_{dialog_nonce}",
                icon=":material/add:",
                help="Create new operation",
                use_container_width=True,
            ):
                st.session_state[ADD_STEP_OPERATION_DIALOG_CREATE_NEW_KEY] = True
                st.rerun()

    if not create_new:
        _render_readonly_operation_preview(
            operation_by_id.get(selected_operation_id), dialog_nonce
        )
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
                _append_operation_to_step(scenario_step, selected_operation_id)
                _close_add_step_operation_dialog()
                st.session_state[SCENARIO_FEEDBACK_KEY] = "Operazione aggiunta."
                st.rerun()
        with action_cols[2]:
            if st.button(
                "Cancel",
                key=f"scenario_add_operation_cancel_existing_{dialog_nonce}",
                use_container_width=True,
            ):
                _close_add_step_operation_dialog()
                st.rerun()
        return

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
        st.text_input(
            "Queue id",
            key=f"scenario_add_operation_queue_id_{dialog_nonce}",
        )
        st.text_input(
            "Template id (optional)",
            key=f"scenario_add_operation_template_id_{dialog_nonce}",
        )
        template_params_key = f"scenario_add_operation_template_params_{dialog_nonce}"
        if template_params_key not in st.session_state:
            st.session_state[template_params_key] = "{}"
        st.text_area(
            "Template params JSON (optional)",
            key=template_params_key,
            height=180,
        )
    elif operation_type == OPERATION_TYPE_SAVE_INTERNAL_DB:
        st.text_input(
            "Table name",
            key=f"scenario_add_operation_internal_table_name_{dialog_nonce}",
        )
    elif operation_type == OPERATION_TYPE_SAVE_EXTERNAL_DB:
        st.text_input(
            "Connection id",
            key=f"scenario_add_operation_connection_id_{dialog_nonce}",
        )
        st.text_input(
            "Table name",
            key=f"scenario_add_operation_external_table_name_{dialog_nonce}",
        )

    create_cols = st.columns([6, 3, 3], gap="small")
    with create_cols[1]:
        if st.button(
            "Save and add",
            key=f"scenario_add_operation_save_and_add_{dialog_nonce}",
            icon=":material/save:",
            type="secondary",
            use_container_width=True,
        ):
            payload, validation_error = _build_operation_creation_payload(dialog_nonce)
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
            _append_operation_to_step(scenario_step, created_operation_id)
            _close_add_step_operation_dialog()
            st.session_state[SCENARIO_FEEDBACK_KEY] = "Nuova operazione creata e aggiunta."
            st.rerun()
    with create_cols[2]:
        if st.button(
            "Cancel",
            key=f"scenario_add_operation_cancel_new_{dialog_nonce}",
            use_container_width=True,
        ):
            _close_add_step_operation_dialog()
            st.rerun()


def _render_editor():
    draft = st.session_state.get(SCENARIO_DRAFT_KEY)
    if not isinstance(draft, dict):
        return

    mode = str(st.session_state.get(SCENARIO_EDITOR_MODE_KEY, "edit"))
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

    st.markdown("**Scenario steps**")
    steps = draft.get("steps") or []

    for step_idx, scenario_step in enumerate(steps):
        _render_step_container(
            draft,
            scenario_step,
            step_idx,
            nonce,
            step_catalog,
            operation_catalog,
            step_labels_by_id,
            operation_labels_by_id,
        )

    if st.button(
        "Add scenario step",
        key=f"scenario_{nonce}_add_step",
        icon=":material/add:",
        use_container_width=True,
    ):
        _open_add_scenario_step_dialog()
        st.rerun()

    if st.session_state.get(ADD_SCENARIO_STEP_DIALOG_OPEN_KEY, False):
        _add_scenario_step_dialog(draft, step_catalog, step_labels_by_id)
    if st.session_state.get(ADD_STEP_OPERATION_DIALOG_OPEN_KEY, False):
        _add_step_operation_dialog(draft, operation_catalog, operation_labels_by_id)


def render_scenarios_page():
    _ensure_editor_context()

    st.header("Scenarios")
    st.caption("Configure scenarios, scenario steps and step operations.")
    
    _render_pending_switch_warning()
    st.divider()

    left_col, right_col = st.columns([2, 5], gap="medium", vertical_alignment="top")
    with left_col:
        _render_left_scenarios_list(st.session_state.get(SCENARIOS_KEY, []))
        add_cols = st.columns([1, 7], gap="small", vertical_alignment="center")
        with add_cols[0]:
            if st.button(
                "",
                key="add_scenario_btn",
                help="Add scenario",
                icon=":material/add:",
                use_container_width=True,
            ):
                _request_create_mode()
    with right_col:
        with st.container(border=True):
            _render_editor()

    if _is_editor_dirty():
        action_cols = st.columns([8, 1, 1], gap="small", vertical_alignment="center")
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

    feedback_message = st.session_state.pop(SCENARIO_FEEDBACK_KEY, None)
    if feedback_message:
        st.success(feedback_message,icon="✅")
