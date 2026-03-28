from copy import deepcopy

import streamlit as st

from database_connections.services.data_loader_service import (
    DATABASE_CONNECTIONS_KEY,
    load_database_connections,
)
from elaborations_shared.services.data_loader_service import load_test_editor_context
from elaborations_shared.services.state_keys import (
    SUITE_FEEDBACK_KEY,
    TEST_EDITOR_BROKERS_KEY,
    TEST_EDITOR_DATABASE_DATASOURCES_KEY,
    TEST_EDITOR_JSON_ARRAYS_KEY,
)
from test_suites.components import suite_editor_component as shared
from test_suites.services.api_service import execute_test_by_id
from test_suites.services.execution_stream_service import register_execution_listener
from test_suites.services.state_keys import (
    SELECTED_TEST_SUITE_ID_KEY,
    TEST_SUITE_DRAFT_KEY,
    TEST_SUITE_LAST_EXECUTION_ID_KEY,
)


def _consume_test_command_dialog_request() -> bool:
    is_open_requested = bool(st.session_state.get(shared.TEST_ADD_COMMAND_DIALOG_OPEN_KEY, False))
    if is_open_requested:
        st.session_state[shared.TEST_ADD_COMMAND_DIALOG_OPEN_KEY] = False
    return is_open_requested


def _render_test_editor_operation(item: dict, operation: dict, op_idx: int, draft: dict):
    item_ui_key = str(item.get("_ui_key") or shared.new_ui_key())
    item["_ui_key"] = item_ui_key
    operation_ui_key = str(operation.get("_ui_key") or f"{item_ui_key}_op_{op_idx}")
    operation["_ui_key"] = operation_ui_key
    operation_index, current_operation = shared._find_operation_by_ui_key(item, operation_ui_key)
    if not isinstance(current_operation, dict):
        return

    is_editing = shared._is_inline_test_command_active(operation_ui_key)
    command_group = shared._resolve_test_command_group(current_operation.get("configuration_json"))
    action_label = shared._command_action_label(current_operation)
    is_first = operation_index <= 0
    is_last = operation_index >= len(shared._operation_list(item)) - 1

    cmd_col, up_col, down_col = st.columns([20, 1, 1], gap="small", vertical_alignment="center")
    with cmd_col:
        with st.container(border=True):
            columns = st.columns([10,10 , 1, 1], gap="small", vertical_alignment="center")
            with columns[0]:
                markdown_label = shared._build_suite_command_markdown(current_operation)
                
                st.markdown(markdown_label)
            
            with columns[1]:
                description = shared._command_description_text(current_operation)
                if description:
                    st.caption(description)

            with columns[2]:
                if st.button(
                    "",
                    key=f"test_editor_inline_command_modify_{item_ui_key}_{operation_ui_key}",
                    icon=":material/edit:",
                    type="tertiary",
                    help=f"Modify {action_label}",
                    use_container_width=True,
                ):
                    shared._open_inline_test_command_editor(operation_ui_key)
                    st.rerun()

            with columns[3]:
                if st.button(
                    "",
                    key=f"test_editor_inline_command_delete_{item_ui_key}_{operation_ui_key}",
                    icon=":material/delete:",
                    help=f"Delete {action_label}",
                    use_container_width=True,
                    type="tertiary",
                ):
                    if shared._delete_operation_by_ui_key(item, operation_ui_key):
                        shared._close_inline_test_command_editor()
                        st.session_state[SUITE_FEEDBACK_KEY] = "Command removed."
                        shared._persist_changes()

            if is_editing:
                if command_group and command_group != "fallback-json":
                    shared._render_inline_typed_test_command_editor(
                        draft,
                        item,
                        current_operation,
                        operation_index,
                        command_group,
                        shared._inline_test_command_nonce(),
                    )
                else:
                    shared._render_inline_generic_test_command_editor(
                        item,
                        current_operation,
                        operation_index,
                        shared._inline_test_command_nonce(),
                    )
                return

        with up_col:
            if st.button(
                "",
                key=f"test_editor_inline_command_up_{item_ui_key}_{operation_ui_key}",
                icon=":material/arrow_upward:",
                help=f"Move {action_label} up",
                disabled=is_first,
                use_container_width=True,
                type="tertiary",
            ):
                original_draft = deepcopy(st.session_state.get(TEST_SUITE_DRAFT_KEY, {}))
                if shared._move_operation_in_item(item, operation_index, operation_index - 1):
                    try:
                        shared._persist_current_draft(success_message="Commands reordered.", rerun=False)
                    except Exception as exc:
                        st.session_state[TEST_SUITE_DRAFT_KEY] = original_draft
                        shared._render_persist_error(exc)
                        return
                    shared._close_inline_test_command_editor()
                    st.rerun()
        with down_col:
            if st.button(
                "",
                key=f"test_editor_inline_command_down_{item_ui_key}_{operation_ui_key}",
                icon=":material/arrow_downward:",
                help=f"Move {action_label} down",
                disabled=is_last,
                use_container_width=True,
                type="tertiary",
            ):
                original_draft = deepcopy(st.session_state.get(TEST_SUITE_DRAFT_KEY, {}))
                if shared._move_operation_in_item(item, operation_index, operation_index + 1):
                    try:
                        shared._persist_current_draft(success_message="Commands reordered.", rerun=False)
                    except Exception as exc:
                        st.session_state[TEST_SUITE_DRAFT_KEY] = original_draft
                        shared._render_persist_error(exc)
                        return
                    shared._close_inline_test_command_editor()
                    st.rerun()


def _render_test_editor_item(test: dict, index: int, draft: dict, execution_state: dict):
    current_test = shared._ensure_test_item(test, index)
    operations = current_test.get("operations") or []
    if operations:
        for op_idx, operation in enumerate(operations):
            _render_test_editor_operation(current_test, operation, op_idx, draft)
    else:
        st.caption("Nessun command configurato.")

    current_test_id = str(current_test.get("id") or "").strip()
    selected_suite_id = str(st.session_state.get(SELECTED_TEST_SUITE_ID_KEY) or "").strip()
    can_run_single_test = bool(current_test_id and selected_suite_id)

    st.divider()
    
    add_cols = st.columns([1, 3, 3, 3, 1, 3], gap="small", vertical_alignment="center")
    with add_cols[1]:
        if st.button(
            "+ Variable",
            key=f"suite_editor_add_test_constant_{current_test.get('_ui_key')}",
            icon=":material/add:",
            use_container_width=True,
        ):
            shared._open_test_command_dialog_for_item(str(current_test.get("_ui_key") or ""), "constant")
            st.rerun()
    with add_cols[2]:
        if st.button(
            "+ Action",
            key=f"suite_editor_add_test_action_{current_test.get('_ui_key')}",
            icon=":material/add:",
            use_container_width=True,
        ):
            shared._open_test_command_dialog_for_item(str(current_test.get("_ui_key") or ""), "action")
            st.rerun()
    with add_cols[3]:
        if st.button(
            "+ Assert",
            key=f"suite_editor_add_test_assert_{current_test.get('_ui_key')}",
            icon=":material/add:",
            use_container_width=True,
        ):
            shared._open_test_command_dialog_for_item(str(current_test.get("_ui_key") or ""), "assert")
            st.rerun()
    with add_cols[5]:
        if st.button(
            "",
            key=f"suite_editor_run_test_{current_test.get('_ui_key')}",
            icon=":material/play_arrow:",
            help="Run this test"
            if can_run_single_test
            else "Save suite before running this test",
            type="primary",
            disabled=not can_run_single_test,
            use_container_width=True,
        ):
            response = execute_test_by_id(selected_suite_id, current_test_id)
            execution_id = str(response.get("execution_id") or "").strip()
            if execution_id:
                st.session_state[TEST_SUITE_LAST_EXECUTION_ID_KEY] = execution_id
                st.session_state[shared.PENDING_TEST_SUITE_EXECUTION_SELECTION_KEY] = execution_id
                register_execution_listener(execution_id, selected_suite_id)
                st.rerun()


@st.dialog("Add test command", width="large")
def _render_add_test_command_dialog(draft: dict):
    dialog_nonce = int(st.session_state.get(shared.TEST_ADD_COMMAND_DIALOG_NONCE_KEY, 0))
    test_ui_key = str(st.session_state.get(shared.TEST_ADD_COMMAND_DIALOG_TARGET_UI_KEY) or "").strip()
    command_group = str(st.session_state.get(shared.TEST_ADD_COMMAND_DIALOG_GROUP_KEY) or "constant").strip().lower()
    test_item = shared._find_test_by_ui_key(draft, test_ui_key)
    command_intro_label = shared._command_group_intro_label(command_group, mode="add")
    primary_action_label = shared._command_group_primary_action_label(command_group, mode="add")

    if not isinstance(test_item, dict):
        st.error("Test di destinazione non trovato.")
        if st.button("Cancel", key=f"suite_test_add_command_missing_cancel_{dialog_nonce}", use_container_width=True):
            shared._close_test_command_dialog()
            st.rerun()
        return

    load_test_editor_context(force=False)
    load_database_connections(force=False)

    json_arrays = shared._safe_list(st.session_state.get(TEST_EDITOR_JSON_ARRAYS_KEY, []))
    datasources = shared._safe_list(st.session_state.get(TEST_EDITOR_DATABASE_DATASOURCES_KEY, []))
    brokers = shared._safe_list(st.session_state.get(TEST_EDITOR_BROKERS_KEY, []))
    connections = shared._safe_list(st.session_state.get(DATABASE_CONNECTIONS_KEY, []))

    st.markdown(f"**{command_intro_label}**")
    command_ui_code = shared._render_test_command_form(
        dialog_nonce,
        command_group,
        json_arrays,
        datasources,
        brokers,
        connections,
        draft,
        test_item,
        stop_before_index=len(shared._operation_list(test_item)),
        key_prefix="suite_test_command",
    )

    action_cols = st.columns([1, 1], gap="small", vertical_alignment="center")
    with action_cols[0]:
        if st.button(
            primary_action_label,
            key=f"suite_add_test_command_save_{dialog_nonce}",
            icon=":material/add_circle:",
            type="secondary",
            use_container_width=True,
        ):
            operation_item, validation_error = shared._build_test_command_draft_with_prefix(
                dialog_nonce,
                command_ui_code,
                key_prefix="suite_test_command",
            )
            if validation_error:
                st.error(validation_error)
                return
            shared.append_operation_to_test(test_item, operation_item or {})
            shared._close_test_command_dialog()
            st.session_state[SUITE_FEEDBACK_KEY] = shared._command_group_added_feedback(command_group)
            shared._persist_changes()
    with action_cols[1]:
        if st.button(
            "Cancel",
            key=f"suite_add_test_command_cancel_{dialog_nonce}",
            use_container_width=True,
        ):
            shared._close_test_command_dialog()
            st.rerun()
