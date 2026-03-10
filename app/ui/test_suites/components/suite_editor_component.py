import streamlit as st

from scenarios.components.scenario_operation_component import (
    render_add_step_operation_dialog,
    render_operation_component,
)
from scenarios.services.data_loader_service import (
    load_operations_catalog,
    load_step_editor_context,
)
from scenarios.services.state_keys import (
    ADD_STEP_OPERATION_DIALOG_NONCE_KEY,
    ADD_STEP_OPERATION_DIALOG_OPEN_KEY,
    ADD_STEP_OPERATION_DIALOG_TARGET_STEP_UI_KEY,
    OPERATIONS_CATALOG_KEY,
)
from test_suites.services.api_service import (
    create_test_suite,
    delete_test_suite_by_id,
    delete_test_suite_execution_by_id,
    execute_test_by_id,
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
    TEST_SUITE_INCLUDE_PREVIOUS_KEY,
    TEST_SUITE_LAST_EXECUTION_ID_KEY,
    TEST_SUITES_KEY,
)

SUITE_HOOK_PHASES = [
    ("before-all", "beforeAll"),
    ("before-each", "beforeEach"),
    ("after-each", "afterEach"),
    ("after-all", "afterAll"),
]


def _new_suite_item(kind: str, hook_phase: str | None = None) -> dict:
    return {
        "id": None,
        "kind": kind,
        "hook_phase": hook_phase,
        "code": hook_phase or "",
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


def _load_selected_draft():
    suite_id = str(st.session_state.get(SELECTED_TEST_SUITE_ID_KEY) or "").strip()
    if not suite_id:
        return
    payload = get_test_suite_by_id(suite_id)
    st.session_state[TEST_SUITE_DRAFT_KEY] = build_test_suite_draft(payload)


def _resolve_editor_draft() -> dict:
    selected_suite_id = str(st.session_state.get(SELECTED_TEST_SUITE_ID_KEY) or "").strip()
    draft = st.session_state.get(TEST_SUITE_DRAFT_KEY)
    if not isinstance(draft, dict):
        if selected_suite_id:
            _load_selected_draft()
            draft = st.session_state.get(TEST_SUITE_DRAFT_KEY)
        if not isinstance(draft, dict):
            draft = build_test_suite_draft({})
            st.session_state[TEST_SUITE_DRAFT_KEY] = draft
        return draft

    draft_suite_id = str(draft.get("id") or "").strip()
    if selected_suite_id and draft_suite_id != selected_suite_id:
        _load_selected_draft()
        updated_draft = st.session_state.get(TEST_SUITE_DRAFT_KEY)
        if isinstance(updated_draft, dict):
            return updated_draft
    if not selected_suite_id and draft_suite_id:
        draft = build_test_suite_draft({})
        st.session_state[TEST_SUITE_DRAFT_KEY] = draft
    return draft


def _persist_changes():
    st.session_state[TEST_SUITE_DRAFT_KEY] = st.session_state.get(TEST_SUITE_DRAFT_KEY, {})


def _open_add_operation_dialog(item_ui_key: str):
    st.session_state[ADD_STEP_OPERATION_DIALOG_OPEN_KEY] = True
    st.session_state[ADD_STEP_OPERATION_DIALOG_TARGET_STEP_UI_KEY] = item_ui_key
    st.session_state[ADD_STEP_OPERATION_DIALOG_NONCE_KEY] = (
        int(st.session_state.get(ADD_STEP_OPERATION_DIALOG_NONCE_KEY, 0)) + 1
    )


def _close_add_operation_dialog():
    st.session_state[ADD_STEP_OPERATION_DIALOG_OPEN_KEY] = False
    st.session_state.pop(ADD_STEP_OPERATION_DIALOG_TARGET_STEP_UI_KEY, None)


def _render_operations(item: dict, execution_state: dict):
    item_ui_key = str(item.get("_ui_key") or new_ui_key())
    item["_ui_key"] = item_ui_key
    operation_status = execution_state.get("operation_status", {})
    operation_error = execution_state.get("operation_error", {})

    for op_idx, operation in enumerate(item.get("operations") or []):
        operation_id = str(operation.get("id") or "").strip()
        op_key = f"{str(item.get('id') or '').strip()}:{operation_id}" if operation_id else ""
        render_operation_component(
            item,
            operation,
            op_idx,
            item_ui_key,
            nonce=0,
            operation_status=str(operation_status.get(op_key) or "idle"),
            operation_error_message=str(operation_error.get(op_key) or ""),
            persist_scenario_changes_fn=_persist_changes,
        )

    if st.button(
        "Add operation",
        key=f"test_suite_add_operation_{item_ui_key}",
        icon=":material/add:",
        type="secondary",
        use_container_width=True,
    ):
        _open_add_operation_dialog(item_ui_key)


def _render_hook_editor(hook_phase: str, hook_label: str, draft: dict, execution_state: dict):
    hooks = draft.setdefault("hooks", {})
    hook = hooks.get(hook_phase)
    with st.expander(f"{hook_label} hook", expanded=False):
        if not isinstance(hook, dict):
            if st.button(
                f"Create {hook_label}",
                key=f"create_hook_{hook_phase}",
                icon=":material/add:",
                type="secondary",
                use_container_width=True,
            ):
                hooks[hook_phase] = _new_suite_item("hook", hook_phase=hook_phase)
                st.rerun()
            return

        hook["code"] = st.text_input(
            "Code",
            value=str(hook.get("code") or hook_phase),
            key=f"hook_code_{hook_phase}_{hook.get('_ui_key')}",
        )
        hook["description"] = st.text_input(
            "Description",
            value=str(hook.get("description") or ""),
            key=f"hook_description_{hook_phase}_{hook.get('_ui_key')}",
        )
        _render_operations(hook, execution_state)
        if st.button(
            f"Remove {hook_label}",
            key=f"remove_hook_{hook_phase}",
            icon=":material/delete:",
            type="secondary",
            use_container_width=True,
        ):
            hooks.pop(hook_phase, None)
            st.rerun()


def _render_test_editor(test: dict, index: int, draft: dict, suite_id: str, execution_state: dict):
    item_id = str(test.get("id") or "")
    item_status = execution_state.get("item_status", {})
    item_error = execution_state.get("item_error", {})
    status = str(item_status.get(item_id) or "idle")
    title = f"Test {index}: {test.get('code') or 'new-test'} [{status}]"
    with st.expander(title, expanded=False):
        cols = st.columns([3, 2], gap="small")
        with cols[0]:
            test["code"] = st.text_input(
                "Code",
                value=str(test.get("code") or ""),
                key=f"test_code_{test.get('_ui_key')}",
            )
        with cols[1]:
            test["on_failure"] = st.selectbox(
                "On failure",
                options=["ABORT", "CONTINUE"],
                index=0 if str(test.get("on_failure") or "ABORT") == "ABORT" else 1,
                key=f"test_on_failure_{test.get('_ui_key')}",
            )
        test["description"] = st.text_input(
            "Description",
            value=str(test.get("description") or ""),
            key=f"test_description_{test.get('_ui_key')}",
        )
        error_message = str(item_error.get(item_id) or "")
        if error_message:
            st.caption(f"Error: {error_message}")

        action_cols = st.columns([1, 1], gap="small")
        with action_cols[0]:
            if st.button(
                "Run test",
                key=f"run_test_{test.get('_ui_key')}",
                icon=":material/play_arrow:",
                type="secondary",
                disabled=not bool(suite_id and item_id),
                use_container_width=True,
            ):
                response = execute_test_by_id(
                    suite_id,
                    item_id,
                    include_previous=bool(st.session_state.get(TEST_SUITE_INCLUDE_PREVIOUS_KEY, False)),
                )
                execution_id = str(response.get("execution_id") or "").strip()
                if execution_id:
                    st.session_state[TEST_SUITE_LAST_EXECUTION_ID_KEY] = execution_id
                    register_execution_listener(execution_id, suite_id)
                    st.rerun()
        with action_cols[1]:
            if st.button(
                "Remove test",
                key=f"remove_test_{test.get('_ui_key')}",
                icon=":material/delete:",
                type="secondary",
                use_container_width=True,
            ):
                draft["tests"] = [
                    item for item in draft.get("tests") or [] if item.get("_ui_key") != test.get("_ui_key")
                ]
                st.rerun()

        _render_operations(test, execution_state)


def _render_history(suite_id: str):
    if not suite_id:
        return
    executions = get_test_suite_executions(suite_id, limit=20)
    st.session_state[TEST_SUITE_EXECUTIONS_KEY] = executions
    st.markdown("**Execution history**")
    for execution in executions:
        execution_id = str(execution.get("id") or "")
        label = (
            f"{execution.get('status') or '-'} | "
            f"{execution.get('started_at') or '-'} | "
            f"{execution.get('requested_test_code') or execution.get('test_suite_code') or execution_id}"
        )
        with st.expander(label, expanded=False):
            st.write(f"Error: {execution.get('error_message') or '-'}")
            for item in execution.get("items") or []:
                st.markdown(
                    f"- {item.get('item_kind')} | {item.get('hook_phase') or item.get('item_code')} | {item.get('status')}"
                )
            if st.button(
                "Delete execution",
                key=f"delete_execution_{execution_id}",
                icon=":material/delete:",
                type="secondary",
                use_container_width=True,
            ):
                delete_test_suite_execution_by_id(execution_id)
                st.rerun()


def render_suite_editor_page():
    load_step_editor_context(force=False)
    load_operations_catalog(force=False)
    suites = _load_test_suites(force=False)
    draft = _resolve_editor_draft()

    suite_labels = {str(item.get("id")): str(item.get("description") or item.get("code") or item.get("id")) for item in suites}
    suite_ids = [str(item.get("id")) for item in suites if item.get("id")]
    current_suite_id = str(st.session_state.get(SELECTED_TEST_SUITE_ID_KEY) or "")
    if suite_ids and current_suite_id not in suite_ids:
        current_suite_id = suite_ids[0]
        st.session_state[SELECTED_TEST_SUITE_ID_KEY] = current_suite_id

    header_cols = st.columns([3, 1, 1, 1], gap="small")
    with header_cols[0]:
        selected_suite_id = st.selectbox(
            "Test suite",
            options=[""] + suite_ids,
            format_func=lambda _id: suite_labels.get(_id, "New suite") if _id else "New suite",
            index=([""] + suite_ids).index(current_suite_id) if current_suite_id in suite_ids else 0,
            key="test_suite_editor_select",
        )
        if selected_suite_id != current_suite_id:
            st.session_state[SELECTED_TEST_SUITE_ID_KEY] = selected_suite_id or None
            if selected_suite_id:
                _load_selected_draft()
            else:
                st.session_state[TEST_SUITE_DRAFT_KEY] = build_test_suite_draft({})
            st.rerun()
    with header_cols[1]:
        if st.button("New", icon=":material/add:", type="secondary", use_container_width=True):
            st.session_state[SELECTED_TEST_SUITE_ID_KEY] = None
            st.session_state[TEST_SUITE_DRAFT_KEY] = build_test_suite_draft({})
            st.rerun()
    with header_cols[2]:
        if st.button("Save", icon=":material/save:", type="secondary", use_container_width=True):
            payload = draft_to_test_suite_payload(draft)
            if draft.get("id"):
                payload["id"] = draft.get("id")
                response = update_test_suite(payload)
                st.session_state[TEST_SUITE_FEEDBACK_KEY] = response.get("message") or "Test suite updated."
            else:
                response = create_test_suite(payload)
                created_id = str(response.get("id") or "").strip()
                st.session_state[SELECTED_TEST_SUITE_ID_KEY] = created_id or None
                st.session_state[TEST_SUITE_FEEDBACK_KEY] = response.get("message") or "Test suite created."
                if created_id:
                    _load_test_suites(force=True)
                    _load_selected_draft()
            st.rerun()
    with header_cols[3]:
        if st.button(
            "Delete",
            icon=":material/delete:",
            type="secondary",
            disabled=not bool(draft.get("id")),
            use_container_width=True,
        ):
            delete_test_suite_by_id(str(draft.get("id")))
            st.session_state[SELECTED_TEST_SUITE_ID_KEY] = None
            st.session_state[TEST_SUITE_DRAFT_KEY] = build_test_suite_draft({})
            _load_test_suites(force=True)
            st.rerun()

    feedback = str(st.session_state.get(TEST_SUITE_FEEDBACK_KEY) or "").strip()
    if feedback:
        st.success(feedback)
        st.session_state.pop(TEST_SUITE_FEEDBACK_KEY, None)

    draft["code"] = st.text_input("Code", value=str(draft.get("code") or ""), key="test_suite_code")
    draft["description"] = st.text_input(
        "Description",
        value=str(draft.get("description") or ""),
        key="test_suite_description",
    )

    exec_cols = st.columns([1, 1, 2], gap="small")
    with exec_cols[0]:
        if st.button(
            "Run suite",
            icon=":material/play_arrow:",
            type="secondary",
            disabled=not bool(draft.get("id")),
            use_container_width=True,
        ):
            response = execute_test_suite_by_id(str(draft.get("id")))
            execution_id = str(response.get("execution_id") or "").strip()
            if execution_id:
                st.session_state[TEST_SUITE_LAST_EXECUTION_ID_KEY] = execution_id
                register_execution_listener(execution_id, str(draft.get("id")))
                st.rerun()
    with exec_cols[1]:
        st.checkbox(
            "Include previous",
            key=TEST_SUITE_INCLUDE_PREVIOUS_KEY,
            help="Used when running a single test.",
        )

    execution_state = get_execution_state(str(st.session_state.get(TEST_SUITE_LAST_EXECUTION_ID_KEY) or ""))
    if execution_state:
        st.info(
            "Test suite running: "
            f"{execution_state.get('executed_tests', 0)}/{execution_state.get('total_tests', 0)} tests executed "
            f"[{execution_state.get('status') or 'running'}]"
        )

    main_cols = st.columns([3, 2], gap="large")
    with main_cols[0]:
        st.markdown("### Hooks")
        for hook_phase, hook_label in SUITE_HOOK_PHASES:
            _render_hook_editor(hook_phase, hook_label, draft, execution_state)

        st.markdown("### Tests")
        if st.button(
            "Add test",
            icon=":material/add:",
            type="secondary",
            use_container_width=True,
        ):
            draft.setdefault("tests", []).append(_new_suite_item("test"))
            st.rerun()

        for index, test in enumerate(draft.get("tests") or [], start=1):
            _render_test_editor(test, index, draft, str(draft.get("id") or ""), execution_state)

    with main_cols[1]:
        _render_history(str(draft.get("id") or ""))

    if bool(st.session_state.get(ADD_STEP_OPERATION_DIALOG_OPEN_KEY, False)):
        operations_catalog = st.session_state.get(OPERATIONS_CATALOG_KEY, [])
        if not isinstance(operations_catalog, list):
            operations_catalog = []
        operation_labels_by_id = {
            str(item.get("id")): str(item.get("description") or item.get("code") or item.get("id"))
            for item in operations_catalog
            if item.get("id")
        }
        render_add_step_operation_dialog(
            draft,
            operations_catalog,
            operation_labels_by_id,
            _close_add_operation_dialog,
            persist_scenario_changes_fn=_persist_changes,
        )
