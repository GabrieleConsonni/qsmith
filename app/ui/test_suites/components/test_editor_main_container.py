import streamlit as st

from elaborations_shared.services.data_loader_service import load_test_editor_context
from test_suites.components import suite_editor_component as shared
from test_suites.services.state_keys import TEST_SUITES_PAGE_PATH


def _go_back():
    st.switch_page(TEST_SUITES_PAGE_PATH)


def render_test_editor_main_container():
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
    selected_test_position = shared._ensure_selected_test_position(draft)
    selected_index, selected_test = shared._find_test_by_position(draft, selected_test_position)
    suite_description = str(draft.get("description") or "").strip() or "Test suite"

    if st.button(
        "Back to test suites",
        key="test_editor_back_btn",
        icon=":material/arrow_back:",
        type="secondary",
    ):
        _go_back()

    shared._render_operation_feedback()

    if not isinstance(selected_test, dict):
        st.markdown("### Test editor")
        st.caption(f"Suite: {suite_description}")
        st.info("Select a test from the suites page.")
        return

    test_label = shared._test_label(selected_test, selected_index)
    st.markdown(f"### {test_label}")
    st.caption(f"Suite: {suite_description}")
    st.divider()

    shared._render_test_editor_item(selected_test, selected_index, draft, {})

    if shared._consume_test_command_dialog_request():
        shared._render_add_test_command_dialog(draft)

    if shared._consume_edit_test_dialog_request():
        shared._render_edit_test_dialog(draft)
