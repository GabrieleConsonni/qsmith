import streamlit as st

from test_suites.services.api_service import (
    create_test_suite,
    delete_test_suite_by_id,
    get_all_test_suites,
    get_test_suite_by_id,
    update_test_suite,
)
from test_suites.services.draft_mapper import (
    build_test_suite_draft,
    draft_to_test_suite_payload,
)
from test_suites.services.state_keys import (
    SELECTED_TEST_SUITE_ID_KEY,
    TEST_SUITE_DRAFT_KEY,
    TEST_SUITE_FEEDBACK_KEY,
    TEST_SUITE_LAST_EXECUTION_ID_KEY,
    TEST_SUITES_KEY,
)

SUITE_EDITOR_PAGE_PATH = "pages/SuiteEditor.py"


def _load_test_suites(force: bool = False) -> list[dict]:
    if force or TEST_SUITES_KEY not in st.session_state:
        st.session_state[TEST_SUITES_KEY] = get_all_test_suites()
    suites = st.session_state.get(TEST_SUITES_KEY, [])
    return suites if isinstance(suites, list) else []


def _open_suite_editor(suite_id: str | None):
    st.session_state[SELECTED_TEST_SUITE_ID_KEY] = suite_id or None
    st.session_state.pop(TEST_SUITE_DRAFT_KEY, None)
    st.session_state.pop(TEST_SUITE_LAST_EXECUTION_ID_KEY, None)
    st.switch_page(SUITE_EDITOR_PAGE_PATH)


def _clear_selected_suite_state(suite_id: str | None = None):
    selected_suite_id = str(st.session_state.get(SELECTED_TEST_SUITE_ID_KEY) or "").strip()
    target_suite_id = str(suite_id or "").strip()
    if not target_suite_id or selected_suite_id == target_suite_id:
        st.session_state.pop(SELECTED_TEST_SUITE_ID_KEY, None)
        st.session_state.pop(TEST_SUITE_DRAFT_KEY, None)
        st.session_state.pop(TEST_SUITE_LAST_EXECUTION_ID_KEY, None)


def _show_feedback():
    feedback = str(st.session_state.get(TEST_SUITE_FEEDBACK_KEY) or "").strip()
    if feedback:
        st.success(feedback)
        st.session_state.pop(TEST_SUITE_FEEDBACK_KEY, None)


@st.dialog("New test suite", width="medium")
def _create_test_suite_dialog():
    dialog_suffix = "test_suite_create"
    st.text_input("Description", key=f"{dialog_suffix}_description")

    action_cols = st.columns([1, 1], gap="small", vertical_alignment="center")
    with action_cols[0]:
        if st.button(
            "Save",
            key=f"{dialog_suffix}_save",
            icon=":material/save:",
            type="secondary",
            use_container_width=True,
        ):
            description = str(st.session_state.get(f"{dialog_suffix}_description") or "")
            if not description.strip():
                st.error("Description is required.")
                return
            try:
                response = create_test_suite(
                    {
                        "description": description,
                        "hooks": [],
                        "tests": [],
                    }
                )
            except Exception as exc:
                st.error(f"Error creating test suite: {str(exc)}")
                return

            created_id = str((response or {}).get("id") or "").strip()
            if not created_id:
                st.error("Error creating test suite: id not returned.")
                return
            _load_test_suites(force=True)
            st.session_state[TEST_SUITE_FEEDBACK_KEY] = response.get("message") or "Test suite created."
            _open_suite_editor(created_id)
    with action_cols[1]:
        if st.button(
            "Cancel",
            key=f"{dialog_suffix}_cancel",
            use_container_width=True,
        ):
            st.rerun()


@st.dialog("Test suite actions", width="medium")
def _edit_test_suite_dialog(suite_item: dict):
    suite_id = str(suite_item.get("id") or "").strip()
    if not suite_id:
        st.error("Invalid test suite.")
        return

    dialog_suffix = f"test_suite_actions_{suite_id}"
    st.text_input(
        "Description",
        key=f"{dialog_suffix}_description",
        value=str(suite_item.get("description") or ""),
    )

    action_cols = st.columns([1, 1, 1], gap="small", vertical_alignment="center")
    with action_cols[0]:
        if st.button(
            "Save",
            key=f"{dialog_suffix}_save",
            icon=":material/save:",
            type="secondary",
            use_container_width=True,
        ):
            description = str(st.session_state.get(f"{dialog_suffix}_description") or "")
            if not description.strip():
                st.error("Description is required.")
                return
            try:
                suite_detail = get_test_suite_by_id(suite_id)
                draft = build_test_suite_draft(suite_detail)
                draft["id"] = suite_id
                draft["description"] = description
                payload = draft_to_test_suite_payload(draft)
                payload["id"] = suite_id
                response = update_test_suite(payload)
            except Exception as exc:
                st.error(f"Error updating test suite: {str(exc)}")
                return

            _load_test_suites(force=True)
            st.session_state[TEST_SUITE_FEEDBACK_KEY] = response.get("message") or "Test suite updated."
            st.rerun()
    with action_cols[1]:
        if st.button(
            "Delete",
            key=f"{dialog_suffix}_delete",
            icon=":material/delete:",
            type="secondary",
            use_container_width=True,
        ):
            try:
                response = delete_test_suite_by_id(suite_id)
            except Exception as exc:
                st.error(f"Error deleting test suite: {str(exc)}")
                return

            _clear_selected_suite_state(suite_id)
            _load_test_suites(force=True)
            st.session_state[TEST_SUITE_FEEDBACK_KEY] = response.get("message") or "Test suite deleted."
            st.rerun()
    with action_cols[2]:
        if st.button(
            "Cancel",
            key=f"{dialog_suffix}_cancel",
            use_container_width=True,
        ):
            st.rerun()


def render_test_suites_page():

    header_cols = st.columns([9, 1], gap="small", vertical_alignment="center")
    with header_cols[1]:
        if st.button(
            "",
            icon=":material/add:",
            key="test_suite_add_btn",
            type="secondary",
            use_container_width=True,
        ):
            _create_test_suite_dialog()

    suites = _load_test_suites(force=False)
    if not suites:
        st.info("No test suites configured.")
        return

    for idx, suite in enumerate(suites):
        suite_id = str(suite.get("id") or "").strip()
        description = str(suite.get("description") or "").strip() or "No description"

        with st.container(border=True):
            row = st.columns([9, 1, 1], gap="small", vertical_alignment="center")
            with row[0]:
                st.write(description)
            with row[1]:
                if st.button(
                    "",
                    key=f"open_suite_editor_{suite_id or idx}",
                    icon=":material/settings:",
                    help="Open suite editor",
                    use_container_width=True,
                ):
                    _open_suite_editor(suite_id)
            with row[2]:
                if st.button(
                    "",
                    key=f"test_suite_actions_{suite_id or idx}",
                    icon=":material/more_vert:",
                    help="Edit description",
                    use_container_width=True,
                ):
                    _edit_test_suite_dialog(suite)

    _show_feedback()
