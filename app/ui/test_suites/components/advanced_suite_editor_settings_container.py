import streamlit as st

from elaborations_shared.services.data_loader_service import load_test_editor_context
from test_suites.components import suite_editor_component as shared
from test_suites.services.state_keys import (
    ADVANCED_SUITE_EDITOR_RETURN_LABEL_KEY,
    ADVANCED_SUITE_EDITOR_RETURN_PAGE_KEY,
    SUITE_EDITOR_PAGE_PATH,
)

HOOK_SECTIONS = [
    ("beforeAll", "Before suite start commands settings"),
    ("beforeEach", "Before each test start commands settings"),
    ("afterEach", "After each test end commands settings"),
    ("afterAll", "After suite end commands settings"),
]


def _go_back():
    return_page = str(st.session_state.get(ADVANCED_SUITE_EDITOR_RETURN_PAGE_KEY) or SUITE_EDITOR_PAGE_PATH).strip()
    st.session_state.pop(ADVANCED_SUITE_EDITOR_RETURN_PAGE_KEY, None)
    st.session_state.pop(ADVANCED_SUITE_EDITOR_RETURN_LABEL_KEY, None)
    st.switch_page(return_page or SUITE_EDITOR_PAGE_PATH)


def render_advanced_suite_editor_settings_container():
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
    suite_description = str(draft.get("description") or "").strip() or "Test suite"
    back_label = str(st.session_state.get(ADVANCED_SUITE_EDITOR_RETURN_LABEL_KEY) or "Back to suite").strip()

    if st.button(
        back_label,
        key="advanced_suite_editor_back_btn",
        icon=":material/arrow_back:",
        type="secondary",
    ):
        _go_back()

    st.markdown("### Advanced settings")
    st.caption(f"Suite: {suite_description}")

    st.divider()
    shared._render_operation_feedback()

    for hook_phase, section_title in HOOK_SECTIONS:
        with st.expander(section_title, expanded=True):
            shared._render_hook_section(draft, hook_phase, section_title, {})

    if shared._consume_add_operation_dialog_request():
        shared._render_add_operation_dialog(draft)

    if shared._consume_hook_command_dialog_request():
        shared._render_add_hook_command_dialog(draft)

    if shared._consume_edit_command_dialog_request():
        shared._render_edit_command_dialog(draft)

    if bool(st.session_state.get(shared.COMMAND_REORDER_DIALOG_OPEN_KEY, False)):
        shared._render_reorder_command_dialog(draft)
