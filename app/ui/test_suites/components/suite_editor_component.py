import streamlit as st

from elaborations_shared.components.test_operation_component import (
    render_add_test_operation_dialog,
    render_operation_component,
)
from elaborations_shared.services.data_loader_service import (
    load_operations_catalog,
    load_test_editor_context,
)
from elaborations_shared.services.state_keys import (
    ADD_TEST_OPERATION_DIALOG_NONCE_KEY,
    ADD_TEST_OPERATION_DIALOG_OPEN_KEY,
    ADD_TEST_OPERATION_DIALOG_TARGET_TEST_UI_KEY,
    OPERATIONS_CATALOG_KEY,
    SUITE_FEEDBACK_KEY,
)
from test_suites.services.api_service import (
    execute_test_suite_by_id,
    get_all_test_suites,
    get_test_suite_by_id,
    get_test_suite_executions,
    update_test_suite,
)
from test_suites.services.draft_mapper import (
    build_test_suite_draft,
    draft_to_test_suite_payload,
    new_ui_key,
)
from test_suites.services.execution_stream_service import (
    get_execution_state,
    register_execution_listener,
)
from test_suites.services.state_keys import (
    SELECTED_TEST_SUITE_ID_KEY,
    TEST_SUITE_DRAFT_KEY,
    TEST_SUITE_EXECUTIONS_KEY,
    TEST_SUITE_FEEDBACK_KEY,
    TEST_SUITE_LAST_EXECUTION_ID_KEY,
    TEST_SUITES_KEY,
)

SELECTED_TEST_SUITE_EXECUTION_ID_KEY = "selected_test_suite_execution_id"
ADD_TEST_DIALOG_OPEN_KEY = "test_suite_add_test_dialog_open"
ADD_TEST_DIALOG_NONCE_KEY = "test_suite_add_test_dialog_nonce"
ACTIVE_SUITE_SECTION_KEY = "active_suite_section"
SUITE_SECTION_PHASES = [
    ("before-all", "beforeAll"),
    ("before-each", "beforeEach"),
    ("tests", "test"),
    ("after-each", "afterEach"),
    ("after-all", "afterAll"),
]


def _new_suite_item(kind: str, hook_phase: str | None = None) -> dict:
    return {
        "id": None,
        "kind": kind,
        "hook_phase": hook_phase,
        "description": "",
        "position": 0,
        "on_failure": "ABORT",
        "operations": [],
        "_ui_key": new_ui_key(),
    }


def _load_test_suites(force: bool = False) -> list[dict]:
    if force or TEST_SUITES_KEY not in st.session_state:
        st.session_state[TEST_SUITES_KEY] = get_all_test_suites()
    suites = st.session_state.get(TEST_SUITES_KEY, [])
    return suites if isinstance(suites, list) else []


def _ensure_selected_suite_id(suites: list[dict]) -> str:
    suite_ids = [str(item.get("id")) for item in suites if item.get("id")]
    current_suite_id = str(st.session_state.get(SELECTED_TEST_SUITE_ID_KEY) or "").strip()
    if current_suite_id in suite_ids:
        return current_suite_id
    selected_suite_id = suite_ids[0] if suite_ids else ""
    st.session_state[SELECTED_TEST_SUITE_ID_KEY] = selected_suite_id or None
    return selected_suite_id


def _load_selected_draft() -> dict:
    suite_id = str(st.session_state.get(SELECTED_TEST_SUITE_ID_KEY) or "").strip()
    if not suite_id:
        draft = build_test_suite_draft({})
        st.session_state[TEST_SUITE_DRAFT_KEY] = draft
        return draft

    payload = get_test_suite_by_id(suite_id)
    draft = build_test_suite_draft(payload)
    st.session_state[TEST_SUITE_DRAFT_KEY] = draft
    return draft


def _resolve_editor_draft(suite_id: str) -> dict:
    draft = st.session_state.get(TEST_SUITE_DRAFT_KEY)
    if not suite_id:
        return draft if isinstance(draft, dict) else _load_selected_draft()

    if not isinstance(draft, dict):
        return _load_selected_draft()

    draft_suite_id = str(draft.get("id") or "").strip()
    if draft_suite_id != suite_id:
        return _load_selected_draft()
    return draft


def _load_execution_history(suite_id: str) -> list[dict]:
    if not suite_id:
        st.session_state[TEST_SUITE_EXECUTIONS_KEY] = []
        st.session_state.pop(SELECTED_TEST_SUITE_EXECUTION_ID_KEY, None)
        return []

    executions = get_test_suite_executions(suite_id, limit=20)
    st.session_state[TEST_SUITE_EXECUTIONS_KEY] = executions

    execution_ids = [str(item.get("id")) for item in executions if item.get("id")]
    selected_execution_id = str(st.session_state.get(SELECTED_TEST_SUITE_EXECUTION_ID_KEY) or "").strip()
    preferred_execution_id = str(st.session_state.get(TEST_SUITE_LAST_EXECUTION_ID_KEY) or "").strip()

    if execution_ids:
        if selected_execution_id not in execution_ids:
            st.session_state[SELECTED_TEST_SUITE_EXECUTION_ID_KEY] = (
                preferred_execution_id if preferred_execution_id in execution_ids else execution_ids[0]
            )
    else:
        st.session_state.pop(SELECTED_TEST_SUITE_EXECUTION_ID_KEY, None)

    return executions if isinstance(executions, list) else []


def _format_execution_label(execution: dict) -> str:
    execution_id = str(execution.get("id") or "").strip() or "-"
    requested_item = str(
        execution.get("requested_test_id")
        or execution.get("test_suite_description")
        or execution_id
    ).strip()
    started_at = str(execution.get("started_at") or "-")
    status = str(execution.get("status") or "-")
    return f"{status} | {started_at} | {requested_item}"


def _find_selected_execution(executions: list[dict]) -> dict | None:
    selected_execution_id = str(st.session_state.get(SELECTED_TEST_SUITE_EXECUTION_ID_KEY) or "").strip()
    for execution in executions:
        if str(execution.get("id") or "").strip() == selected_execution_id:
            return execution
    return None


def _render_execution_summary(execution: dict | None):
    if not isinstance(execution, dict):
        return

    with st.container(border=True):
        cols = st.columns(3, gap="small")
        with cols[0]:
            st.caption("Status")
            st.write(str(execution.get("status") or "-"))
        with cols[1]:
            st.caption("Started at")
            st.write(str(execution.get("started_at") or "-"))
        with cols[2]:
            st.caption("Requested item")
            st.write(
                str(
                    execution.get("requested_test_id")
                    or execution.get("test_suite_description")
                    or "-"
                )
            )

        error_message = str(execution.get("error_message") or "").strip()
        if error_message:
            st.error(error_message)


def _persist_changes():
    draft = st.session_state.get(TEST_SUITE_DRAFT_KEY, {})
    if isinstance(draft, dict) and str(draft.get("id") or "").strip():
        payload = draft_to_test_suite_payload(draft)
        payload["id"] = str(draft.get("id") or "").strip()
        update_test_suite(payload)
        _load_selected_draft()
        _load_test_suites(force=True)
        st.session_state[TEST_SUITE_FEEDBACK_KEY] = "Test suite updated."
    else:
        st.session_state[TEST_SUITE_DRAFT_KEY] = draft
    st.rerun()


def _render_operation_feedback():
    suite_feedback = str(st.session_state.pop(TEST_SUITE_FEEDBACK_KEY, "") or "").strip()
    if suite_feedback:
        st.success(suite_feedback)
    feedback = str(st.session_state.pop(SUITE_FEEDBACK_KEY, "") or "").strip()
    if feedback:
        st.success(feedback)


def _close_add_operation_dialog():
    st.session_state[ADD_TEST_OPERATION_DIALOG_OPEN_KEY] = False
    st.session_state.pop(ADD_TEST_OPERATION_DIALOG_TARGET_TEST_UI_KEY, None)


def _consume_add_operation_dialog_request() -> bool:
    is_open_requested = bool(st.session_state.get(ADD_TEST_OPERATION_DIALOG_OPEN_KEY, False))
    if is_open_requested:
        st.session_state[ADD_TEST_OPERATION_DIALOG_OPEN_KEY] = False
    return is_open_requested


def _open_add_test_dialog():
    st.session_state[ADD_TEST_DIALOG_OPEN_KEY] = True
    st.session_state[ADD_TEST_DIALOG_NONCE_KEY] = int(st.session_state.get(ADD_TEST_DIALOG_NONCE_KEY, 0)) + 1


def _close_add_test_dialog():
    st.session_state[ADD_TEST_DIALOG_OPEN_KEY] = False

def _get_hook_item(draft: dict, hook_phase: str) -> dict | None:
    hooks = draft.get("hooks")
    if not isinstance(hooks, dict):
        return None

    hook = hooks.get(hook_phase)
    if not isinstance(hook, dict):
        return None

    hook["_ui_key"] = str(hook.get("_ui_key") or new_ui_key())
    operations = hook.get("operations")
    if not isinstance(operations, list):
        hook["operations"] = []
    return hook


def _ensure_hook_item(draft: dict, hook_phase: str) -> dict:
    hooks = draft.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        hooks = {}
        draft["hooks"] = hooks

    hook = _get_hook_item(draft, hook_phase)
    if isinstance(hook, dict):
        return hook

    hook = _new_suite_item("hook", hook_phase=hook_phase)
    hooks[hook_phase] = hook
    return hook


def _open_add_operation_dialog_for_hook(draft: dict, hook_phase: str):
    hook = _ensure_hook_item(draft, hook_phase)
    _open_add_operation_dialog_for_item(str(hook.get("_ui_key") or ""))


def _open_add_operation_dialog_for_item(item_ui_key: str):
    st.session_state[ADD_TEST_OPERATION_DIALOG_OPEN_KEY] = True
    st.session_state[ADD_TEST_OPERATION_DIALOG_TARGET_TEST_UI_KEY] = str(item_ui_key or "")
    st.session_state[ADD_TEST_OPERATION_DIALOG_NONCE_KEY] = (
        int(st.session_state.get(ADD_TEST_OPERATION_DIALOG_NONCE_KEY, 0)) + 1
    )


def _operation_state_key(item_id: object, operation_id: object) -> str:
    normalized_item_id = str(item_id or "").strip()
    normalized_operation_id = str(operation_id or "").strip()
    if not normalized_item_id or not normalized_operation_id:
        return ""
    return f"{normalized_item_id}:{normalized_operation_id}"


def _render_suite_item_operation(
    item: dict,
    operation: dict,
    op_idx: int,
    _parent_label: str,
    execution_state: dict,
):
    item_ui_key = str(item.get("_ui_key") or new_ui_key())
    item["_ui_key"] = item_ui_key
    operation_key = _operation_state_key(item.get("id"), operation.get("id"))
    operation_status = str((execution_state.get("operation_status") or {}).get(operation_key) or "idle")
    operation_error = str((execution_state.get("operation_error") or {}).get(operation_key) or "").strip()
    render_operation_component(
        suite_test=item,
        operation=operation,
        op_idx=op_idx,
        test_ui_key=item_ui_key,
        nonce=0,
        operation_status=operation_status,
        operation_error_message=operation_error,
        persist_suite_changes_fn=_persist_changes,
        summary_only=True,
    )


def _render_section(section_title: str, summary: str):
    st.markdown(f"### {section_title}")
    if summary:
        st.caption(summary)


def _render_section_summary(summary: str):
    if summary:
        st.caption(summary)


def _render_hook_section(draft: dict, hook_phase: str, hook_label: str, execution_state: dict):
    hook = _get_hook_item(draft, hook_phase)
    operations = hook.get("operations") if isinstance(hook, dict) else []

    if operations:
        for op_idx, operation in enumerate(operations):
            _render_suite_item_operation(hook, operation, op_idx, hook_label, execution_state)
    else:
        st.caption("Nessuna operation configurata.")

    add_cols = st.columns([8, 2], gap="small", vertical_alignment="center")
    with add_cols[1]:
        if st.button(
            "Add operation",
            key=f"suite_editor_add_operation_{hook_phase}_{str((hook or {}).get('_ui_key') or hook_phase)}",
            icon=":material/add:",
            use_container_width=True,
        ):
            _open_add_operation_dialog_for_hook(draft, hook_phase)
            st.rerun()


def _ensure_test_item(test: dict, index: int) -> dict:
    test["_ui_key"] = str(test.get("_ui_key") or new_ui_key())
    if not isinstance(test.get("operations"), list):
        test["operations"] = []
    if not str(test.get("kind") or "").strip():
        test["kind"] = "test"
    return test


def _test_label(test: dict, index: int) -> str:
    description = str(test.get("description") or "").strip()
    test_id = str(test.get("id") or "").strip()
    return description or test_id or f"Test {index}"


def _render_test_item(test: dict, index: int, execution_state: dict):
    current_test = _ensure_test_item(test, index)
    with st.expander(_test_label(current_test, index), expanded=False):
        operations = current_test.get("operations") or []
        if operations:
            for op_idx, operation in enumerate(operations):
                _render_suite_item_operation(current_test, operation, op_idx, _test_label(current_test, index), execution_state)
        else:
            st.caption("Nessuna operation configurata.")

        add_cols = st.columns([8, 2], gap="small", vertical_alignment="center")
        with add_cols[1]:
            if st.button(
                "Add operation",
                key=f"suite_editor_add_test_operation_{current_test.get('_ui_key')}",
                icon=":material/add:",
                use_container_width=True,
            ):
                _open_add_operation_dialog_for_item(str(current_test.get("_ui_key") or ""))
                st.rerun()


@st.dialog("Add operation", width="large")
def _render_add_operation_dialog(draft: dict):
    operations_catalog = st.session_state.get(OPERATIONS_CATALOG_KEY, [])
    if not isinstance(operations_catalog, list):
        operations_catalog = []

    operation_labels_by_id = {
        str(item.get("id")): str(item.get("description") or item.get("id"))
        for item in operations_catalog
        if item.get("id")
    }
    render_add_test_operation_dialog(
        draft,
        operations_catalog,
        operation_labels_by_id,
        _close_add_operation_dialog,
        persist_suite_changes_fn=_persist_changes,
    )


@st.dialog("Add test", width="medium")
def _render_add_test_dialog(draft: dict):
    dialog_nonce = int(st.session_state.get(ADD_TEST_DIALOG_NONCE_KEY, 0))
    description_key = f"test_suite_add_test_description_{dialog_nonce}"
    st.text_input(
        "Description",
        key=description_key,
        placeholder="Test description",
    )

    action_cols = st.columns([1, 1], gap="small", vertical_alignment="center")
    with action_cols[0]:
        if st.button(
            "Save",
            key=f"test_suite_add_test_save_{dialog_nonce}",
            icon=":material/save:",
            type="secondary",
            use_container_width=True,
        ):
            description = str(st.session_state.get(description_key) or "").strip()
            if not description:
                st.error("Il campo Description del test e' obbligatorio.")
                return
            tests = draft.setdefault("tests", [])
            if not isinstance(tests, list):
                tests = []
                draft["tests"] = tests

            tests.append(
                {
                    **_new_suite_item("test"),
                    "description": description,
                    "position": len(tests) + 1,
                }
            )
            _close_add_test_dialog()
            _persist_changes()
    with action_cols[1]:
        if st.button(
            "Cancel",
            key=f"test_suite_add_test_cancel_{dialog_nonce}",
            use_container_width=True,
        ):
            _close_add_test_dialog()
            st.rerun()


def render_suite_editor_page():
    load_test_editor_context(force=False)
    load_operations_catalog(force=False)

    suites = _load_test_suites(force=False)
    if not suites:
        st.info("No test suites configured.")
        return

    selected_suite_id = _ensure_selected_suite_id(suites)
    if not selected_suite_id:
        st.info("Select a test suite from the suites page.")
        return

    draft = _resolve_editor_draft(selected_suite_id)
    executions = _load_execution_history(selected_suite_id)

    suite_description = str(draft.get("description") or "").strip() or "Test suite"
    execution_options = [str(item.get("id")) for item in executions if item.get("id")]
    history_options = execution_options or [""]
    selected_execution_id = str(st.session_state.get(SELECTED_TEST_SUITE_EXECUTION_ID_KEY) or "").strip()

    header_cols = st.columns([4, 3, 1], gap="small", vertical_alignment="bottom")
    with header_cols[0]:
        st.markdown(f"### {suite_description}")
    with header_cols[1]:
        st.selectbox(
            "Execution history",
            options=history_options,
            index=history_options.index(selected_execution_id) if selected_execution_id in history_options else 0,
            format_func=lambda execution_id: (
                "No executions"
                if not execution_id
                else _format_execution_label(
                    next(
                        (
                            execution
                            for execution in executions
                            if str(execution.get("id") or "").strip() == execution_id
                        ),
                        {"id": execution_id},
                    )
                )
            ),
            key=SELECTED_TEST_SUITE_EXECUTION_ID_KEY,
            disabled=not bool(execution_options),
            label_visibility="collapsed",
        )
    with header_cols[2]:
        if st.button(
            "Run",
            key="run_suite",
            icon=":material/play_arrow:",
            type="secondary",
            use_container_width=True,
        ):
            response = execute_test_suite_by_id(selected_suite_id)
            execution_id = str(response.get("execution_id") or "").strip()
            if execution_id:
                st.session_state[TEST_SUITE_LAST_EXECUTION_ID_KEY] = execution_id
                st.session_state[SELECTED_TEST_SUITE_EXECUTION_ID_KEY] = execution_id
                register_execution_listener(execution_id, selected_suite_id)
                st.rerun()

    st.divider()

    execution_state = get_execution_state(str(st.session_state.get(TEST_SUITE_LAST_EXECUTION_ID_KEY) or ""))
    if execution_state:
        st.info(
            "Test suite running: "
            f"{execution_state.get('executed_tests', 0)}/{execution_state.get('total_tests', 0)} tests executed "
            f"[{execution_state.get('status') or 'running'}]"
        )

    _render_operation_feedback()
    _render_execution_summary(_find_selected_execution(executions))

    execution_state_map = execution_state if isinstance(execution_state, dict) else {}
    tests = draft.get("tests") or []
    phase_labels = {phase: label for phase, label in SUITE_SECTION_PHASES}
    active_section = st.segmented_control(
        "Suite sections",
        options=[phase for phase, _ in SUITE_SECTION_PHASES],
        default=st.session_state.get(ACTIVE_SUITE_SECTION_KEY) or SUITE_SECTION_PHASES[0][0],
        format_func=lambda phase: phase_labels.get(str(phase), str(phase)),
        key=ACTIVE_SUITE_SECTION_KEY,
        label_visibility="collapsed",
    )
    active_phase = str(active_section or SUITE_SECTION_PHASES[0][0])
    active_label = phase_labels.get(active_phase, active_phase)

    if active_phase == "tests":
        if tests:
            for index, test in enumerate(tests, start=1):
                _render_test_item(test, index, execution_state_map)
        else:
            st.caption("Nessun test configurato.")
        add_cols = st.columns([8, 2], gap="small", vertical_alignment="center")
        with add_cols[1]:
            if st.button(
                "Add test",
                key="suite_editor_add_test",
                icon=":material/add:",
                use_container_width=True,
            ):
                _open_add_test_dialog()
                st.rerun()
    else:
        hook = _get_hook_item(draft, active_phase)
        operations = hook.get("operations") if isinstance(hook, dict) else []
        total_operations = len(operations or [])
        summary = f"{total_operations} operation configurate." if total_operations else ""
        _render_section_summary(summary)
        _render_hook_section(draft, active_phase, active_label, execution_state_map)

    if _consume_add_operation_dialog_request():
        _render_add_operation_dialog(draft)

    if bool(st.session_state.get(ADD_TEST_DIALOG_OPEN_KEY, False)):
        _render_add_test_dialog(draft)

