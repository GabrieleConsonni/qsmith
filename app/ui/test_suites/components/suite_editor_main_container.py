import streamlit as st

from elaborations_shared.services.data_loader_service import load_test_editor_context
from test_suites.components import suite_editor_component as shared
from test_suites.services.api_service import execute_test_suite_by_id
from test_suites.services.execution_stream_service import register_execution_listener
from test_suites.services.state_keys import (
    ADVANCED_SUITE_EDITOR_PAGE_PATH,
    ADVANCED_SUITE_EDITOR_RETURN_LABEL_KEY,
    ADVANCED_SUITE_EDITOR_RETURN_PAGE_KEY,
    SUITE_EDITOR_PAGE_PATH,
    TEST_SUITE_LAST_EXECUTION_ID_KEY,
)


def _open_advanced_settings():
    st.session_state[ADVANCED_SUITE_EDITOR_RETURN_PAGE_KEY] = SUITE_EDITOR_PAGE_PATH
    st.session_state[ADVANCED_SUITE_EDITOR_RETURN_LABEL_KEY] = "Back to suite"
    st.switch_page(ADVANCED_SUITE_EDITOR_PAGE_PATH)


def render_suite_editor_main_container():
    load_test_editor_context(force=False)

    suites = shared._load_test_suites(force=False)
    if not suites:
        st.info("No test suites configured.")
        return

    selected_suite_id = shared._ensure_selected_suite_id(suites)
    if not selected_suite_id:
        st.info("Select a test suite from the suites page.")
        return

    draft = shared._resolve_editor_draft(selected_suite_id)
    executions = shared._load_execution_history(selected_suite_id)

    suite_description = str(draft.get("description") or "").strip() or "Test suite"
    execution_options = [str(item.get("id")) for item in executions if item.get("id")]
    history_options = execution_options or [""]
    selected_execution_id = str(
        st.session_state.get(shared.SELECTED_TEST_SUITE_EXECUTION_ID_KEY) or ""
    ).strip()

    header_cols = st.columns([4, 3, 1, 1], gap="small", vertical_alignment="bottom")
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
                else shared._format_execution_label(
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
            key=shared.SELECTED_TEST_SUITE_EXECUTION_ID_KEY,
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
                st.session_state[shared.PENDING_TEST_SUITE_EXECUTION_SELECTION_KEY] = execution_id
                register_execution_listener(execution_id, selected_suite_id)
                st.rerun()
    with header_cols[3]:
        if st.button(
            "",
            key="suite_editor_advanced_settings",
            icon=":material/settings:",
            help="Advance settings",
            type="secondary",
            use_container_width=True,
        ):
            _open_advanced_settings()

    st.divider()

    shared._render_operation_feedback()

    tests = draft.get("tests") or []
    if tests:
        for index, test in enumerate(tests, start=1):
            shared._render_test_item(test, index, {})
    else:
        st.caption("Nessun test configurato.")

    st.divider()

    add_cols = st.columns([8, 2], gap="small", vertical_alignment="center")
    with add_cols[1]:
        if st.button(
            "",
            key="suite_editor_add_test",
            icon=":material/add:",
            use_container_width=True,
        ):
            shared._open_add_test_dialog()
            st.rerun()

    if shared._consume_add_operation_dialog_request():
        shared._render_add_operation_dialog(draft)

    if shared._consume_test_command_dialog_request():
        shared._render_add_test_command_dialog(draft)

    if shared._consume_edit_command_dialog_request():
        shared._render_edit_command_dialog(draft)

    if bool(st.session_state.get(shared.COMMAND_REORDER_DIALOG_OPEN_KEY, False)):
        shared._render_reorder_command_dialog(draft)

    if shared._consume_edit_test_dialog_request():
        shared._render_edit_test_dialog(draft)

    if bool(st.session_state.get(shared.ADD_TEST_DIALOG_OPEN_KEY, False)):
        shared._render_add_test_dialog(draft)
