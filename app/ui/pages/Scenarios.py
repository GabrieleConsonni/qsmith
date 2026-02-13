from copy import deepcopy
from decimal import Decimal
from uuid import uuid4

import streamlit as st

from api_client import api_delete, api_get, api_post, api_put


SCENARIOS_KEY = "scenarios"
STEPS_CATALOG_KEY = "steps_catalog"
OPERATIONS_CATALOG_KEY = "operations_catalog"
SELECTED_SCENARIO_ID_KEY = "selected_scenario_id"
SCENARIO_EDITOR_MODE_KEY = "scenario_editor_mode"
SCENARIO_DRAFT_KEY = "scenario_draft"
SCENARIO_BASELINE_PAYLOAD_KEY = "scenario_baseline_payload"
SCENARIO_EDITOR_NONCE_KEY = "scenario_editor_nonce"
SCENARIO_FEEDBACK_KEY = "scenarios_feedback"
PENDING_SCENARIO_SWITCH_KEY = "pending_scenario_switch"

ON_FAILURE_OPTIONS = ["ABORT", "CONTINUE"]


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
    if reset_baseline:
        _set_baseline_payload_from_draft(draft)
    _clear_pending_switch()
    _bump_editor_nonce()


def _load_scenarios(force: bool = False):
    if force or SCENARIOS_KEY not in st.session_state:
        try:
            scenarios = api_get("/elaborations/scenario")
        except Exception:
            scenarios = []
            st.error("Errore caricamento scenari.")
        st.session_state[SCENARIOS_KEY] = scenarios if isinstance(scenarios, list) else []


def _load_steps_catalog(force: bool = False):
    if force or STEPS_CATALOG_KEY not in st.session_state:
        try:
            steps = api_get("/elaborations/step")
        except Exception:
            steps = []
            st.error("Errore caricamento steps.")
        st.session_state[STEPS_CATALOG_KEY] = steps if isinstance(steps, list) else []


def _load_operations_catalog(force: bool = False):
    if force or OPERATIONS_CATALOG_KEY not in st.session_state:
        try:
            operations = api_get("/elaborations/operation")
        except Exception:
            operations = []
            st.error("Errore caricamento operations.")
        st.session_state[OPERATIONS_CATALOG_KEY] = (
            operations if isinstance(operations, list) else []
        )


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


def _new_draft_operation(default_operation_id: str = "", order: int = 1) -> dict:
    return {
        "id": None,
        "order": order,
        "operation_id": default_operation_id,
        "_ui_key": _new_ui_key(),
        "_edit_mode": True,
    }


def _new_draft_step(default_step_id: str = "", order: int = 1) -> dict:
    return {
        "id": None,
        "order": order,
        "step_id": default_step_id,
        "on_failure": "ABORT",
        "operations": [],
        "_ui_key": _new_ui_key(),
        "_edit_mode": True,
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
        scenario = api_get(f"/elaborations/scenario/{scenario_id}")
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
    _load_scenarios(force=force)
    _load_steps_catalog(force=force)
    _load_operations_catalog(force=force)


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
            response = api_post("/elaborations/scenario", payload)
            scenario_id = response.get("id") if isinstance(response, dict) else None
            feedback = "Scenario creato."
        else:
            scenario_id = str(draft.get("id"))
            api_put(
                "/elaborations/scenario",
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
        api_delete(f"/elaborations/scenario/{scenario_id}")
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
        api_get(f"/elaborations/scenario/{scenario_id}/execute")
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
        st.info("Nessuno scenario configurato.")
        return

    for idx, scenario in enumerate(scenarios):
        scenario_id = str(scenario.get("id") or "")
        code = scenario.get("code") or "-"
        description = scenario.get("description") or "-"
        is_selected = mode != "create" and str(selected_id) == scenario_id
        with st.container(border=True):
            if st.button(
                code,
                key=f"select_scenario_btn_{scenario_id or idx}",
                type="primary" if is_selected else "secondary",
                use_container_width=True,
                help="Select scenario",
            ):
                _request_select_scenario(scenario_id)
            st.caption(description)

            action_cols = st.columns([8, 1, 1], gap="small", vertical_alignment="center")
            with action_cols[1]:
                if st.button(
                    "",
                    key=f"execute_scenario_btn_{scenario_id or idx}",
                    icon=":material/play_arrow:",
                    help="Execute scenario",
                    use_container_width=True,
                ):
                    _execute_scenario(scenario_id)
            with action_cols[2]:
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
                operation_options = [str(item.get("id")) for item in operation_catalog if item.get("id")]
                if operation_options:
                    current_operation_id = str(operation.get("operation_id") or "")
                    if current_operation_id and current_operation_id not in operation_options:
                        operation_options.insert(0, current_operation_id)
                    selected_operation_id = st.selectbox(
                        "Operation",
                        options=operation_options,
                        index=(
                            operation_options.index(current_operation_id)
                            if current_operation_id in operation_options
                            else 0
                        ),
                        format_func=lambda _id: operation_labels_by_id.get(_id, f"Unknown ({_id})"),
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
            operation_label = operation_labels_by_id.get(operation_id, f"Unknown ({operation_id})")
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
                index=ON_FAILURE_OPTIONS.index(on_failure) if on_failure in ON_FAILURE_OPTIONS else 0,
                key=f"scenario_{nonce}_step_on_failure_{step_ui_key}",
            )
        else:
            st.caption(f"on_failure: {scenario_step.get('on_failure') or 'ABORT'}")

        st.markdown("**Step operations**")
        operations = scenario_step.get("operations") or []
        if not operations:
            st.info("Nessuna operation configurata.")
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

        default_operation_id = ""
        if operation_catalog and operation_catalog[0].get("id"):
            default_operation_id = str(operation_catalog[0].get("id"))
        if st.button(
            "Add operation",
            key=f"scenario_{nonce}_step_add_operation_{step_ui_key}",
            icon=":material/add:",
            use_container_width=True,
        ):
            scenario_step.setdefault("operations", []).append(
                _new_draft_operation(
                    default_operation_id=default_operation_id,
                    order=len(operations) + 1,
                )
            )
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


def _render_editor():
    draft = st.session_state.get(SCENARIO_DRAFT_KEY)
    if not isinstance(draft, dict):
        st.info("Seleziona uno scenario dalla lista a sinistra.")
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
    if not steps:
        st.info("Nessuno scenario step configurato.")

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

    default_step_id = ""
    if step_catalog and step_catalog[0].get("id"):
        default_step_id = str(step_catalog[0].get("id"))
    if st.button(
        "Add scenario step",
        key=f"scenario_{nonce}_add_step",
        icon=":material/add:",
        use_container_width=True,
    ):
        draft.setdefault("steps", []).append(
            _new_draft_step(default_step_id=default_step_id, order=len(steps) + 1)
        )
        st.rerun()


_ensure_editor_context()

st.header("Scenarios")
st.caption("Configure scenarios, scenario steps and step operations.")
feedback_message = st.session_state.pop(SCENARIO_FEEDBACK_KEY, None)
if feedback_message:
    st.success(feedback_message)
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
