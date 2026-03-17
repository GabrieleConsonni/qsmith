import json

import streamlit as st

from database_connections.services.data_loader_service import (
    DATABASE_CONNECTIONS_KEY,
    load_database_connections,
)
from elaborations_shared.components.test_command_component import (
    append_operation_to_test,
    find_draft_test_by_ui_key,
    render_add_test_operation_dialog,
)
from elaborations_shared.services.data_loader_service import (
    load_test_editor_context,
    load_test_editor_queues_for_broker,
)
from elaborations_shared.services.state_keys import (
    ADD_TEST_OPERATION_DIALOG_NONCE_KEY,
    ADD_TEST_OPERATION_DIALOG_OPEN_KEY,
    ADD_TEST_OPERATION_DIALOG_TARGET_TEST_UI_KEY,
    SUITE_FEEDBACK_KEY,
    TEST_EDITOR_BROKERS_KEY,
    TEST_EDITOR_DATABASE_DATASOURCES_KEY,
    TEST_EDITOR_JSON_ARRAYS_KEY,
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
PENDING_TEST_SUITE_EXECUTION_SELECTION_KEY = "pending_test_suite_execution_selection"
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
HOOK_ADD_COMMAND_DIALOG_OPEN_KEY = "suite_editor_hook_add_command_dialog_open"
HOOK_ADD_COMMAND_DIALOG_NONCE_KEY = "suite_editor_hook_add_command_dialog_nonce"
HOOK_ADD_COMMAND_DIALOG_TARGET_UI_KEY = "suite_editor_hook_add_command_dialog_target_ui_key"
HOOK_ADD_COMMAND_DIALOG_GROUP_KEY = "suite_editor_hook_add_command_dialog_group"
TEST_ADD_COMMAND_DIALOG_OPEN_KEY = "suite_editor_test_add_command_dialog_open"
TEST_ADD_COMMAND_DIALOG_NONCE_KEY = "suite_editor_test_add_command_dialog_nonce"
TEST_ADD_COMMAND_DIALOG_TARGET_UI_KEY = "suite_editor_test_add_command_dialog_target_ui_key"
TEST_ADD_COMMAND_DIALOG_GROUP_KEY = "suite_editor_test_add_command_dialog_group"
TEST_EDIT_DIALOG_OPEN_KEY = "suite_editor_test_edit_dialog_open"
TEST_EDIT_DIALOG_NONCE_KEY = "suite_editor_test_edit_dialog_nonce"
TEST_EDIT_DIALOG_TARGET_UI_KEY = "suite_editor_test_edit_dialog_target_ui_key"
COMMAND_EDIT_DIALOG_OPEN_KEY = "suite_editor_command_edit_dialog_open"
COMMAND_EDIT_DIALOG_NONCE_KEY = "suite_editor_command_edit_dialog_nonce"
COMMAND_EDIT_DIALOG_TARGET_ITEM_UI_KEY = "suite_editor_command_edit_dialog_target_item_ui_key"
COMMAND_EDIT_DIALOG_TARGET_COMMAND_UI_KEY = "suite_editor_command_edit_dialog_target_command_ui_key"
COMMAND_EDIT_DIALOG_OWNER_KIND_KEY = "suite_editor_command_edit_dialog_owner_kind"
COMMAND_EDIT_DIALOG_GROUP_KEY = "suite_editor_command_edit_dialog_group"
HOOK_CONTEXT_COMMAND_CODES = ["initConstant", "deleteConstant"]
HOOK_ACTION_COMMAND_CODES = [
    "saveTable",
    "dropTable",
    "cleanTable",
    "exportDataset",
    "dropDataset",
    "cleanDataset",
]
TEST_CONSTANT_COMMAND_CODES = ["initConstant"]
TEST_ASSERT_COMMAND_CODES = [
    "jsonEquals",
    "jsonEmpty",
    "jsonNotEmpty",
    "jsonContains",
    "jsonArrayEquals",
    "jsonArrayEmpty",
    "jsonArrayNotEmpty",
    "jsonArrayContains",
]
TEST_ACTION_COMMAND_OPTIONS = [
    ("sendMessageQueue", "sendMessageQueue"),
    ("saveTable", "saveTable"),
    ("exportTable", "exportTable"),
    ("dropTable", "dropTable"),
    ("cleanTable", "cleanTable"),
    ("exportDataset", "exportDataset"),
    ("dropDataset", "dropDataset"),
    ("cleanDataset", "cleanDataset"),
]
TEST_ACTION_COMMAND_MAPPING = {
    "sendMessageQueue": "sendMessageQueue",
    "saveTable": "saveTable",
    "exportTable": "exportDataset",
    "dropTable": "dropTable",
    "cleanTable": "cleanTable",
    "exportDataset": "exportDataset",
    "dropDataset": "dropDataset",
    "cleanDataset": "cleanDataset",
}
HOOK_COMMAND_LABELS = {
    "initConstant": "initConstant",
    "deleteConstant": "deleteConstant",
    "saveTable": "saveTable",
    "dropTable": "dropTable",
    "cleanTable": "cleanTable",
    "exportDataset": "exportDataset",
    "dropDataset": "dropDataset",
    "cleanDataset": "cleanDataset",
}
CONSTANT_CONTEXT_OPTIONS = ["runEnvelope", "global", "local", "result"]
TEST_CONSTANT_CONTEXT_OPTIONS = ["local", "result", "global", "runEnvelope"]
CONSTANT_SOURCE_OPTIONS = ["raw", "json", "jsonArray", "dataset", "sqsQueue"]
EXPORT_DATASET_MODE_OPTIONS = ["append", "drop-create", "insert-update"]
SOURCE_COMPATIBILITY_BY_COMMAND = {
    "sendMessageQueue": {"raw", "json", "jsonArray", "dataset"},
    "saveTable": {"json", "jsonArray", "dataset"},
    "exportDataset": {"json", "jsonArray", "dataset"},
}
READABLE_SCOPES_BY_SECTION = {
    "beforeAll": {"runEnvelope", "result"},
    "beforeEach": {"runEnvelope", "global", "result"},
    "test": {"runEnvelope", "global", "local", "result"},
    "afterEach": {"runEnvelope", "global", "local", "result"},
    "afterAll": {"runEnvelope", "global", "result"},
}


def _safe_list(value: object) -> list[dict]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _safe_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    raw = str(value or "").strip()
    if not raw:
        return default
    try:
        return int(float(raw))
    except ValueError:
        return default


def _normalize_context_path(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if raw.startswith("$."):
        return raw
    if raw.startswith("$"):
        return f"$.{raw[1:].lstrip('.')}"
    return f"$.{raw.lstrip('.')}"


def _parse_json_input(value: object) -> tuple[object | None, str | None]:
    if value is None:
        return None, None
    if isinstance(value, (dict, list, int, float, bool)):
        return value, None
    raw = str(value or "").strip()
    if not raw:
        return None, None
    try:
        return json.loads(raw), None
    except json.JSONDecodeError as exc:
        return None, f"JSON non valido: {str(exc)}"


def _parse_json_or_ref_input(value: object) -> tuple[object | None, str | None]:
    raw = str(value or "").strip()
    if not raw:
        return None, None
    if raw == "$" or raw.startswith("$."):
        return raw, None
    return _parse_json_input(raw)


def _parse_csv_tokens(value: object) -> list[str]:
    raw = str(value or "").replace(";", ",").replace("\n", ",")
    return [item.strip() for item in raw.split(",") if item and item.strip()]


def _format_lookup_label(item: dict, fallback_key: str = "id") -> str:
    return str(item.get("description") or item.get("code") or item.get(fallback_key) or "-")


def _safe_dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _command_form_key(prefix: str, dialog_nonce: int, field: str) -> str:
    return f"{prefix}_{field}_{dialog_nonce}"


def _normalize_command_code(configuration_json: dict | None) -> str:
    cfg = _safe_dict(configuration_json)
    return str(cfg.get("commandCode") or cfg.get("command_code") or "").strip()


def _normalize_command_type(configuration_json: dict | None) -> str:
    cfg = _safe_dict(configuration_json)
    return str(cfg.get("commandType") or cfg.get("command_type") or "").strip().lower()


def _stringify_form_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=True, indent=2)


def _csv_from_value(value: object) -> str:
    if isinstance(value, list):
        return ", ".join(str(item).strip() for item in value if str(item).strip())
    return str(value or "").strip()


def _find_broker_id_for_queue_id(queue_id: str, brokers: list[dict]) -> str:
    normalized_queue_id = str(queue_id or "").strip()
    if not normalized_queue_id:
        return ""
    for broker in brokers:
        broker_id = str(broker.get("id") or "").strip()
        if not broker_id:
            continue
        queues = load_test_editor_queues_for_broker(broker_id, force=False)
        if any(str(queue.get("id") or "").strip() == normalized_queue_id for queue in queues):
            return broker_id
    return ""


def _section_type_for_item(item: dict | None) -> str:
    if not isinstance(item, dict):
        return "test"
    if str(item.get("kind") or "").strip().lower() != "hook":
        return "test"
    mapping = {
        "before-all": "beforeAll",
        "before-each": "beforeEach",
        "after-each": "afterEach",
        "after-all": "afterAll",
    }
    return mapping.get(str(item.get("hook_phase") or "").strip().lower(), "test")


def _find_hook_by_phase(draft: dict, hook_phase: str) -> dict | None:
    hooks = draft.get("hooks") or {}
    if not isinstance(hooks, dict):
        return None
    hook = hooks.get(hook_phase)
    return hook if isinstance(hook, dict) else None


def _operation_list(item: dict | None) -> list[dict]:
    operations = item.get("operations") if isinstance(item, dict) else []
    return [operation for operation in operations if isinstance(operation, dict)] if isinstance(operations, list) else []


def _command_result_constant(configuration_json: dict) -> tuple[str, str] | None:
    result_constant = _safe_dict(
        configuration_json.get("resultConstant") or configuration_json.get("result_constant")
    )
    result_name = str(result_constant.get("name") or "").strip()
    result_type = str(
        result_constant.get("valueType") or result_constant.get("value_type") or "json"
    ).strip() or "json"
    if result_name:
        return result_name, result_type

    result_target = _normalize_context_path(
        configuration_json.get("result_target") or configuration_json.get("resultTarget")
    )
    if result_target.startswith("$.result.constants."):
        return result_target.split(".")[-1], "json"
    return None


def _apply_visible_constant_effect(active_definitions: list[dict], operation: dict):
    configuration_json = _safe_dict(operation.get("configuration_json") or {})
    command_code = _normalize_command_code(configuration_json)

    if command_code == "deleteConstant":
        target_name = str(configuration_json.get("name") or "").strip()
        target_context = str(
            configuration_json.get("context") or configuration_json.get("scope") or ""
        ).strip()
        if target_name and target_context:
            for index in range(len(active_definitions) - 1, -1, -1):
                definition = active_definitions[index]
                if (
                    str(definition.get("name") or "").strip() == target_name
                    and str(definition.get("context") or "").strip() == target_context
                ):
                    active_definitions.pop(index)
                    break
        return

    if command_code == "initConstant":
        name = str(configuration_json.get("name") or "").strip()
        context = str(
            configuration_json.get("context") or configuration_json.get("scope") or ""
        ).strip()
        source_type = str(
            configuration_json.get("sourceType") or configuration_json.get("source_type") or ""
        ).strip()
        if name and context and source_type:
            active_definitions.append(
                {
                    "name": name,
                    "context": context,
                    "value_type": source_type,
                    "path": f"$.{context}.constants.{name}",
                }
            )

    result_constant = _command_result_constant(configuration_json)
    if result_constant is not None:
        result_name, result_type = result_constant
        active_definitions.append(
            {
                "name": result_name,
                "context": "result",
                "value_type": result_type,
                "path": f"$.result.constants.{result_name}",
            }
        )


def _collect_visible_constants_from_operations(
    active_definitions: list[dict],
    item: dict | None,
    *,
    stop_before_index: int | None = None,
):
    operations = _operation_list(item)
    for op_index, operation in enumerate(operations):
        if stop_before_index is not None and op_index >= stop_before_index:
            break
        _apply_visible_constant_effect(active_definitions, operation)


def _resolve_available_source_constants(
    draft: dict,
    item: dict,
    *,
    command_code: str,
    stop_before_index: int | None = None,
) -> list[dict]:
    compatible_types = SOURCE_COMPATIBILITY_BY_COMMAND.get(str(command_code or "").strip(), set())
    if not compatible_types:
        return []

    active_definitions: list[dict] = []
    section_type = _section_type_for_item(item)

    before_all_hook = _find_hook_by_phase(draft, "before-all")
    before_each_hook = _find_hook_by_phase(draft, "before-each")

    if section_type in {"beforeEach", "test", "afterEach", "afterAll"}:
        _collect_visible_constants_from_operations(active_definitions, before_all_hook)

    if section_type in {"beforeEach", "test", "afterEach"}:
        _collect_visible_constants_from_operations(active_definitions, before_each_hook)

    if section_type in {"beforeAll", "beforeEach", "afterEach", "afterAll", "test"}:
        _collect_visible_constants_from_operations(
            active_definitions,
            item,
            stop_before_index=stop_before_index,
        )

    filtered_definitions = [
        definition
        for definition in active_definitions
        if str(definition.get("value_type") or "").strip() in compatible_types
        and str(definition.get("context") or "").strip()
        in READABLE_SCOPES_BY_SECTION.get(section_type, set())
    ]

    deduped_by_path: dict[str, dict] = {}
    for definition in filtered_definitions:
        path = str(definition.get("path") or "").strip()
        if path:
            deduped_by_path[path] = definition

    options = list(deduped_by_path.values())
    options.sort(
        key=lambda item: (
            str(item.get("context") or ""),
            str(item.get("name") or ""),
            str(item.get("value_type") or ""),
        )
    )
    return options


def _render_source_constant_select(
    *,
    label: str,
    key: str,
    options: list[dict],
    help_text: str | None = None,
):
    option_values = [str(item.get("path") or "").strip() for item in options if str(item.get("path") or "").strip()]
    current_value = str(st.session_state.get(key) or "").strip()
    if current_value not in option_values:
        st.session_state[key] = option_values[0] if option_values else ""

    st.selectbox(
        label,
        options=option_values or [""],
        format_func=lambda path: (
            next(
                (
                    f"{item.get('name')} [{item.get('context')}] : {item.get('value_type')}"
                    for item in options
                    if str(item.get("path") or "").strip() == str(path or "").strip()
                ),
                "Nessuna costante disponibile",
            )
        ),
        key=key,
        disabled=not bool(option_values),
        help=help_text,
    )
    if not option_values:
        st.info("Nessuna costante compatibile disponibile nel punto corrente.")


def _build_suite_command_markdown(command_item: dict) -> str:
    configuration_json = _safe_dict(command_item.get("configuration_json") or {})
    command_code = _normalize_command_code(configuration_json) or "-"
    command_type = _normalize_command_type(configuration_json)
    description = str(command_item.get("description") or "").strip() or "-"
    constant_name = str(configuration_json.get("name") or "").strip() or "-"
    source_type = str(configuration_json.get("sourceType") or configuration_json.get("source_type") or "").strip() or "-"

    if command_type == "context":
        if command_code == "initConstant":
            return f"**[{command_code}] {constant_name} : {source_type}** - {description}"
        return f"**[{command_code}] {constant_name}** - {description}"
    if command_type in {"action", "assert"}:
        return f"**[{command_code}]** - {description}"
    return f"**[{command_code}]** - {description}"


def _default_context_for_hook_phase(hook_phase: str) -> str:
    normalized_phase = str(hook_phase or "").strip().lower()
    if normalized_phase in {"before-all", "after-all"}:
        return "global"
    return "local"


def _default_context_for_item(item: dict | None) -> str:
    if not isinstance(item, dict):
        return "local"
    if str(item.get("kind") or "").strip().lower() == "hook":
        return _default_context_for_hook_phase(str(item.get("hook_phase") or ""))
    return "local"


def _resolve_hook_command_group(configuration_json: dict | None) -> str:
    command_code = _normalize_command_code(configuration_json)
    command_type = _normalize_command_type(configuration_json)
    if command_type == "context" and command_code in HOOK_CONTEXT_COMMAND_CODES:
        return "context"
    if command_type == "action" and command_code in HOOK_ACTION_COMMAND_CODES:
        return "action"
    return ""


def _resolve_test_command_group(configuration_json: dict | None) -> str:
    command_code = _normalize_command_code(configuration_json)
    command_type = _normalize_command_type(configuration_json)
    if command_type == "context" and command_code in TEST_CONSTANT_COMMAND_CODES:
        return "constant"
    if command_type == "action" and command_code in TEST_ACTION_COMMAND_MAPPING.values():
        return "action"
    if command_type == "assert" and command_code in TEST_ASSERT_COMMAND_CODES:
        return "assert"
    return ""


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
        st.session_state.pop(PENDING_TEST_SUITE_EXECUTION_SELECTION_KEY, None)
        return []

    executions = get_test_suite_executions(suite_id, limit=20)
    st.session_state[TEST_SUITE_EXECUTIONS_KEY] = executions

    execution_ids = [str(item.get("id")) for item in executions if item.get("id")]
    selected_execution_id = str(st.session_state.get(SELECTED_TEST_SUITE_EXECUTION_ID_KEY) or "").strip()
    preferred_execution_id = str(st.session_state.get(TEST_SUITE_LAST_EXECUTION_ID_KEY) or "").strip()
    pending_execution_id = str(st.session_state.get(PENDING_TEST_SUITE_EXECUTION_SELECTION_KEY) or "").strip()

    if execution_ids:
        next_selected_execution_id = selected_execution_id if selected_execution_id in execution_ids else ""

        if pending_execution_id and pending_execution_id in execution_ids:
            next_selected_execution_id = pending_execution_id
            st.session_state.pop(PENDING_TEST_SUITE_EXECUTION_SELECTION_KEY, None)
        elif not next_selected_execution_id:
            next_selected_execution_id = (
                preferred_execution_id if preferred_execution_id in execution_ids else execution_ids[0]
            )

        if next_selected_execution_id and next_selected_execution_id != selected_execution_id:
            st.session_state[SELECTED_TEST_SUITE_EXECUTION_ID_KEY] = next_selected_execution_id
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


def _open_hook_command_dialog_for_hook(draft: dict, hook_phase: str, group: str):
    hook = _ensure_hook_item(draft, hook_phase)
    st.session_state[HOOK_ADD_COMMAND_DIALOG_OPEN_KEY] = True
    st.session_state[HOOK_ADD_COMMAND_DIALOG_TARGET_UI_KEY] = str(hook.get("_ui_key") or "")
    st.session_state[HOOK_ADD_COMMAND_DIALOG_GROUP_KEY] = str(group or "context").strip().lower()
    st.session_state[HOOK_ADD_COMMAND_DIALOG_NONCE_KEY] = (
        int(st.session_state.get(HOOK_ADD_COMMAND_DIALOG_NONCE_KEY, 0)) + 1
    )


def _open_test_command_dialog_for_item(item_ui_key: str, group: str):
    st.session_state[TEST_ADD_COMMAND_DIALOG_OPEN_KEY] = True
    st.session_state[TEST_ADD_COMMAND_DIALOG_TARGET_UI_KEY] = str(item_ui_key or "")
    st.session_state[TEST_ADD_COMMAND_DIALOG_GROUP_KEY] = str(group or "constant").strip().lower()
    st.session_state[TEST_ADD_COMMAND_DIALOG_NONCE_KEY] = (
        int(st.session_state.get(TEST_ADD_COMMAND_DIALOG_NONCE_KEY, 0)) + 1
    )


def _close_test_command_dialog():
    st.session_state[TEST_ADD_COMMAND_DIALOG_OPEN_KEY] = False
    st.session_state.pop(TEST_ADD_COMMAND_DIALOG_TARGET_UI_KEY, None)
    st.session_state.pop(TEST_ADD_COMMAND_DIALOG_GROUP_KEY, None)


def _consume_test_command_dialog_request() -> bool:
    is_open_requested = bool(st.session_state.get(TEST_ADD_COMMAND_DIALOG_OPEN_KEY, False))
    if is_open_requested:
        st.session_state[TEST_ADD_COMMAND_DIALOG_OPEN_KEY] = False
    return is_open_requested


def _open_edit_test_dialog(item_ui_key: str):
    st.session_state[TEST_EDIT_DIALOG_OPEN_KEY] = True
    st.session_state[TEST_EDIT_DIALOG_TARGET_UI_KEY] = str(item_ui_key or "")
    st.session_state[TEST_EDIT_DIALOG_NONCE_KEY] = (
        int(st.session_state.get(TEST_EDIT_DIALOG_NONCE_KEY, 0)) + 1
    )


def _close_edit_test_dialog():
    st.session_state[TEST_EDIT_DIALOG_OPEN_KEY] = False
    st.session_state.pop(TEST_EDIT_DIALOG_TARGET_UI_KEY, None)


def _open_edit_command_dialog(item_ui_key: str, command_ui_key: str, owner_kind: str, command_group: str):
    st.session_state[COMMAND_EDIT_DIALOG_OPEN_KEY] = True
    st.session_state[COMMAND_EDIT_DIALOG_TARGET_ITEM_UI_KEY] = str(item_ui_key or "")
    st.session_state[COMMAND_EDIT_DIALOG_TARGET_COMMAND_UI_KEY] = str(command_ui_key or "")
    st.session_state[COMMAND_EDIT_DIALOG_OWNER_KIND_KEY] = str(owner_kind or "").strip().lower()
    st.session_state[COMMAND_EDIT_DIALOG_GROUP_KEY] = str(command_group or "").strip().lower()
    st.session_state[COMMAND_EDIT_DIALOG_NONCE_KEY] = (
        int(st.session_state.get(COMMAND_EDIT_DIALOG_NONCE_KEY, 0)) + 1
    )


def _close_edit_command_dialog():
    st.session_state[COMMAND_EDIT_DIALOG_OPEN_KEY] = False
    st.session_state.pop(COMMAND_EDIT_DIALOG_TARGET_ITEM_UI_KEY, None)
    st.session_state.pop(COMMAND_EDIT_DIALOG_TARGET_COMMAND_UI_KEY, None)
    st.session_state.pop(COMMAND_EDIT_DIALOG_OWNER_KIND_KEY, None)
    st.session_state.pop(COMMAND_EDIT_DIALOG_GROUP_KEY, None)


def _close_hook_command_dialog():
    st.session_state[HOOK_ADD_COMMAND_DIALOG_OPEN_KEY] = False
    st.session_state.pop(HOOK_ADD_COMMAND_DIALOG_TARGET_UI_KEY, None)
    st.session_state.pop(HOOK_ADD_COMMAND_DIALOG_GROUP_KEY, None)


def _consume_hook_command_dialog_request() -> bool:
    is_open_requested = bool(st.session_state.get(HOOK_ADD_COMMAND_DIALOG_OPEN_KEY, False))
    if is_open_requested:
        st.session_state[HOOK_ADD_COMMAND_DIALOG_OPEN_KEY] = False
    return is_open_requested


def _consume_edit_test_dialog_request() -> bool:
    is_open_requested = bool(st.session_state.get(TEST_EDIT_DIALOG_OPEN_KEY, False))
    if is_open_requested:
        st.session_state[TEST_EDIT_DIALOG_OPEN_KEY] = False
    return is_open_requested


def _consume_edit_command_dialog_request() -> bool:
    is_open_requested = bool(st.session_state.get(COMMAND_EDIT_DIALOG_OPEN_KEY, False))
    if is_open_requested:
        st.session_state[COMMAND_EDIT_DIALOG_OPEN_KEY] = False
    return is_open_requested


def _find_operation_index_by_ui_key(item: dict, operation_ui_key: str) -> int:
    operations = item.get("operations") or []
    if not isinstance(operations, list):
        return -1
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict):
            continue
        current_ui_key = str(operation.get("_ui_key") or "")
        if not current_ui_key:
            current_ui_key = f"{str(item.get('_ui_key') or '')}_op_{index}"
            operation["_ui_key"] = current_ui_key
        if current_ui_key == str(operation_ui_key or ""):
            return index
    return -1


def _find_operation_by_ui_key(item: dict, operation_ui_key: str) -> tuple[int, dict | None]:
    operation_index = _find_operation_index_by_ui_key(item, operation_ui_key)
    operations = item.get("operations") or []
    if operation_index < 0 or not isinstance(operations, list):
        return -1, None
    operation = operations[operation_index]
    return operation_index, operation if isinstance(operation, dict) else None


def _update_operation_in_item(item: dict, operation_index: int, updated_operation: dict):
    operations = item.get("operations") or []
    if not isinstance(operations, list) or not (0 <= operation_index < len(operations)):
        return
    existing_operation = operations[operation_index]
    if not isinstance(existing_operation, dict):
        existing_operation = {}
    operations[operation_index] = {
        **existing_operation,
        **updated_operation,
        "id": existing_operation.get("id"),
        "order": existing_operation.get("order", operation_index + 1),
        "_ui_key": existing_operation.get("_ui_key"),
    }


def _build_hook_command_draft(dialog_nonce: int, command_code: str) -> tuple[dict | None, str | None]:
    description = str(
        st.session_state.get(f"suite_add_hook_command_description_{dialog_nonce}") or ""
    ).strip()
    if not description:
        return None, "Il campo Description e' obbligatorio."

    cfg: dict[str, object]
    if command_code == "initConstant":
        name = str(st.session_state.get(f"suite_add_hook_init_constant_name_{dialog_nonce}") or "").strip()
        context = str(
            st.session_state.get(f"suite_add_hook_init_constant_context_{dialog_nonce}") or "local"
        ).strip()
        source_type = str(
            st.session_state.get(f"suite_add_hook_init_constant_source_type_{dialog_nonce}") or "raw"
        ).strip()
        if not name:
            return None, "Il campo Name e' obbligatorio."
        cfg = {
            "commandCode": "initConstant",
            "commandType": "context",
            "name": name,
            "context": context,
            "sourceType": source_type,
        }
        if source_type in {"raw", "json"}:
            parsed_value, parse_error = _parse_json_input(
                st.session_state.get(f"suite_add_hook_init_constant_value_{dialog_nonce}")
            )
            if parse_error:
                return None, parse_error
            cfg["value"] = parsed_value
        elif source_type == "jsonArray":
            json_array_id = str(
                st.session_state.get(f"suite_add_hook_init_constant_json_array_id_{dialog_nonce}") or ""
            ).strip()
            if not json_array_id:
                return None, "Il campo Json array e' obbligatorio."
            cfg["json_array_id"] = json_array_id
        elif source_type == "dataset":
            dataset_id = str(
                st.session_state.get(f"suite_add_hook_init_constant_dataset_id_{dialog_nonce}") or ""
            ).strip()
            if not dataset_id:
                return None, "Il campo Dataset e' obbligatorio."
            cfg["dataset_id"] = dataset_id
        elif source_type == "sqsQueue":
            queue_id = str(
                st.session_state.get(f"suite_add_hook_init_constant_queue_id_{dialog_nonce}") or ""
            ).strip()
            if not queue_id:
                return None, "Il campo Queue e' obbligatorio."
            cfg["queue_id"] = queue_id
            cfg["retry"] = _safe_int(
                st.session_state.get(f"suite_add_hook_init_constant_retry_{dialog_nonce}"),
                3,
            )
            cfg["wait_time_seconds"] = _safe_int(
                st.session_state.get(f"suite_add_hook_init_constant_wait_time_seconds_{dialog_nonce}"),
                20,
            )
            cfg["max_messages"] = _safe_int(
                st.session_state.get(f"suite_add_hook_init_constant_max_messages_{dialog_nonce}"),
                1000,
            )
    elif command_code == "deleteConstant":
        name = str(st.session_state.get(f"suite_add_hook_delete_constant_name_{dialog_nonce}") or "").strip()
        context = str(
            st.session_state.get(f"suite_add_hook_delete_constant_context_{dialog_nonce}") or "local"
        ).strip()
        if not name:
            return None, "Il campo Name e' obbligatorio."
        cfg = {
            "commandCode": "deleteConstant",
            "commandType": "context",
            "name": name,
            "context": context,
        }
    elif command_code == "saveTable":
        table_name = str(st.session_state.get(f"suite_add_hook_save_table_name_{dialog_nonce}") or "").strip()
        source = _normalize_context_path(
            st.session_state.get(f"suite_add_hook_save_table_source_{dialog_nonce}")
        )
        if not table_name:
            return None, "Il campo Table name e' obbligatorio."
        if not source:
            return None, "Il campo Source constant e' obbligatorio."
        cfg = {
            "commandCode": "saveTable",
            "commandType": "action",
            "table_name": table_name,
        }
        result_target = _normalize_context_path(
            st.session_state.get(f"suite_add_hook_save_table_result_target_{dialog_nonce}")
        )
        cfg["source"] = source
        if result_target:
            cfg["result_target"] = result_target
    elif command_code == "dropTable":
        table_name = str(st.session_state.get(f"suite_add_hook_drop_table_name_{dialog_nonce}") or "").strip()
        if not table_name:
            return None, "Il campo Table name e' obbligatorio."
        cfg = {
            "commandCode": "dropTable",
            "commandType": "action",
            "table_name": table_name,
        }
    elif command_code == "cleanTable":
        table_name = str(st.session_state.get(f"suite_add_hook_clean_table_name_{dialog_nonce}") or "").strip()
        if not table_name:
            return None, "Il campo Table name e' obbligatorio."
        cfg = {
            "commandCode": "cleanTable",
            "commandType": "action",
            "table_name": table_name,
        }
    elif command_code == "exportDataset":
        connection_id = str(
            st.session_state.get(f"suite_add_hook_export_dataset_connection_id_{dialog_nonce}") or ""
        ).strip()
        table_name = str(
            st.session_state.get(f"suite_add_hook_export_dataset_table_name_{dialog_nonce}") or ""
        ).strip()
        if not connection_id:
            return None, "Il campo Connection e' obbligatorio."
        if not table_name:
            return None, "Il campo Table name e' obbligatorio."
        source = _normalize_context_path(
            st.session_state.get(f"suite_add_hook_export_dataset_source_{dialog_nonce}")
        )
        if not source:
            return None, "Il campo Source constant e' obbligatorio."
        cfg = {
            "commandCode": "exportDataset",
            "commandType": "action",
            "connection_id": connection_id,
            "table_name": table_name,
            "mode": str(
                st.session_state.get(f"suite_add_hook_export_dataset_mode_{dialog_nonce}") or "append"
            ).strip(),
        }
        dataset_id = str(
            st.session_state.get(f"suite_add_hook_export_dataset_dataset_id_{dialog_nonce}") or ""
        ).strip()
        dataset_description = str(
            st.session_state.get(f"suite_add_hook_export_dataset_dataset_description_{dialog_nonce}") or ""
        ).strip()
        result_target = _normalize_context_path(
            st.session_state.get(f"suite_add_hook_export_dataset_result_target_{dialog_nonce}")
        )
        mapping_keys = _parse_csv_tokens(
            st.session_state.get(f"suite_add_hook_export_dataset_mapping_keys_{dialog_nonce}")
        )
        cfg["source"] = source
        if dataset_id:
            cfg["dataset_id"] = dataset_id
        if dataset_description:
            cfg["dataset_description"] = dataset_description
        if result_target:
            cfg["result_target"] = result_target
        if mapping_keys:
            cfg["mapping_keys"] = mapping_keys
    elif command_code == "dropDataset":
        dataset_id = str(
            st.session_state.get(f"suite_add_hook_drop_dataset_id_{dialog_nonce}") or ""
        ).strip()
        if not dataset_id:
            return None, "Il campo Dataset e' obbligatorio."
        cfg = {
            "commandCode": "dropDataset",
            "commandType": "action",
            "dataset_id": dataset_id,
        }
    elif command_code == "cleanDataset":
        dataset_id = str(
            st.session_state.get(f"suite_add_hook_clean_dataset_id_{dialog_nonce}") or ""
        ).strip()
        if not dataset_id:
            return None, "Il campo Dataset e' obbligatorio."
        cfg = {
            "commandCode": "cleanDataset",
            "commandType": "action",
            "dataset_id": dataset_id,
        }
    else:
        return None, f"Command type non supportato: {command_code}"

    return {
        "description": description,
        "operation_type": command_code,
        "configuration_json": cfg,
    }, None


def _build_test_command_draft(dialog_nonce: int, command_ui_code: str) -> tuple[dict | None, str | None]:
    description = str(
        st.session_state.get(f"suite_add_test_command_description_{dialog_nonce}") or ""
    ).strip()
    if not description:
        return None, "Il campo Description e' obbligatorio."

    command_code = TEST_ACTION_COMMAND_MAPPING.get(command_ui_code, command_ui_code)
    cfg: dict[str, object]
    if command_code == "initConstant":
        name = str(st.session_state.get(f"suite_add_test_init_constant_name_{dialog_nonce}") or "").strip()
        context = str(
            st.session_state.get(f"suite_add_test_init_constant_context_{dialog_nonce}") or "local"
        ).strip()
        source_type = str(
            st.session_state.get(f"suite_add_test_init_constant_source_type_{dialog_nonce}") or "raw"
        ).strip()
        if not name:
            return None, "Il campo Name e' obbligatorio."
        cfg = {
            "commandCode": "initConstant",
            "commandType": "context",
            "name": name,
            "context": context,
            "sourceType": source_type,
        }
        if source_type in {"raw", "json"}:
            parsed_value, parse_error = _parse_json_input(
                st.session_state.get(f"suite_add_test_init_constant_value_{dialog_nonce}")
            )
            if parse_error:
                return None, parse_error
            cfg["value"] = parsed_value
        elif source_type == "jsonArray":
            json_array_id = str(
                st.session_state.get(f"suite_add_test_init_constant_json_array_id_{dialog_nonce}") or ""
            ).strip()
            if not json_array_id:
                return None, "Il campo Json array e' obbligatorio."
            cfg["json_array_id"] = json_array_id
        elif source_type == "dataset":
            dataset_id = str(
                st.session_state.get(f"suite_add_test_init_constant_dataset_id_{dialog_nonce}") or ""
            ).strip()
            if not dataset_id:
                return None, "Il campo Dataset e' obbligatorio."
            cfg["dataset_id"] = dataset_id
        elif source_type == "sqsQueue":
            queue_id = str(
                st.session_state.get(f"suite_add_test_init_constant_queue_id_{dialog_nonce}") or ""
            ).strip()
            if not queue_id:
                return None, "Il campo Queue e' obbligatorio."
            cfg["queue_id"] = queue_id
            cfg["retry"] = _safe_int(
                st.session_state.get(f"suite_add_test_init_constant_retry_{dialog_nonce}"),
                3,
            )
            cfg["wait_time_seconds"] = _safe_int(
                st.session_state.get(f"suite_add_test_init_constant_wait_time_seconds_{dialog_nonce}"),
                20,
            )
            cfg["max_messages"] = _safe_int(
                st.session_state.get(f"suite_add_test_init_constant_max_messages_{dialog_nonce}"),
                1000,
            )
    elif command_code == "sendMessageQueue":
        queue_id = str(
            st.session_state.get(f"suite_add_test_send_message_queue_id_{dialog_nonce}") or ""
        ).strip()
        source = _normalize_context_path(
            st.session_state.get(f"suite_add_test_send_message_source_{dialog_nonce}")
        )
        if not queue_id:
            return None, "Il campo Queue e' obbligatorio."
        if not source:
            return None, "Il campo Source constant e' obbligatorio."
        cfg = {
            "commandCode": "sendMessageQueue",
            "commandType": "action",
            "queue_id": queue_id,
        }
        template_id = str(
            st.session_state.get(f"suite_add_test_send_message_template_id_{dialog_nonce}") or ""
        ).strip()
        template_params, parse_error = _parse_json_input(
            st.session_state.get(f"suite_add_test_send_message_template_params_{dialog_nonce}")
        )
        if parse_error:
            return None, parse_error
        result_target = _normalize_context_path(
            st.session_state.get(f"suite_add_test_send_message_result_target_{dialog_nonce}")
        )
        cfg["source"] = source
        if template_id:
            cfg["template_id"] = template_id
        if isinstance(template_params, dict):
            cfg["template_params"] = template_params
        if result_target:
            cfg["result_target"] = result_target
    elif command_code == "saveTable":
        table_name = str(st.session_state.get(f"suite_add_test_save_table_name_{dialog_nonce}") or "").strip()
        source = _normalize_context_path(
            st.session_state.get(f"suite_add_test_save_table_source_{dialog_nonce}")
        )
        if not table_name:
            return None, "Il campo Table name e' obbligatorio."
        if not source:
            return None, "Il campo Source constant e' obbligatorio."
        cfg = {
            "commandCode": "saveTable",
            "commandType": "action",
            "table_name": table_name,
        }
        result_target = _normalize_context_path(
            st.session_state.get(f"suite_add_test_save_table_result_target_{dialog_nonce}")
        )
        cfg["source"] = source
        if result_target:
            cfg["result_target"] = result_target
    elif command_code == "dropTable":
        table_name = str(st.session_state.get(f"suite_add_test_drop_table_name_{dialog_nonce}") or "").strip()
        if not table_name:
            return None, "Il campo Table name e' obbligatorio."
        cfg = {
            "commandCode": "dropTable",
            "commandType": "action",
            "table_name": table_name,
        }
    elif command_code == "cleanTable":
        table_name = str(st.session_state.get(f"suite_add_test_clean_table_name_{dialog_nonce}") or "").strip()
        if not table_name:
            return None, "Il campo Table name e' obbligatorio."
        cfg = {
            "commandCode": "cleanTable",
            "commandType": "action",
            "table_name": table_name,
        }
    elif command_code == "exportDataset":
        connection_id = str(
            st.session_state.get(f"suite_add_test_export_dataset_connection_id_{dialog_nonce}") or ""
        ).strip()
        table_name = str(
            st.session_state.get(f"suite_add_test_export_dataset_table_name_{dialog_nonce}") or ""
        ).strip()
        if not connection_id:
            return None, "Il campo Connection e' obbligatorio."
        if not table_name:
            return None, "Il campo Table name e' obbligatorio."
        source = _normalize_context_path(
            st.session_state.get(f"suite_add_test_export_dataset_source_{dialog_nonce}")
        )
        if not source:
            return None, "Il campo Source constant e' obbligatorio."
        cfg = {
            "commandCode": "exportDataset",
            "commandType": "action",
            "connection_id": connection_id,
            "table_name": table_name,
            "mode": str(
                st.session_state.get(f"suite_add_test_export_dataset_mode_{dialog_nonce}") or "append"
            ).strip(),
        }
        dataset_id = str(
            st.session_state.get(f"suite_add_test_export_dataset_dataset_id_{dialog_nonce}") or ""
        ).strip()
        dataset_description = str(
            st.session_state.get(f"suite_add_test_export_dataset_dataset_description_{dialog_nonce}") or ""
        ).strip()
        result_target = _normalize_context_path(
            st.session_state.get(f"suite_add_test_export_dataset_result_target_{dialog_nonce}")
        )
        mapping_keys = _parse_csv_tokens(
            st.session_state.get(f"suite_add_test_export_dataset_mapping_keys_{dialog_nonce}")
        )
        cfg["source"] = source
        if dataset_id:
            cfg["dataset_id"] = dataset_id
        if dataset_description:
            cfg["dataset_description"] = dataset_description
        if result_target:
            cfg["result_target"] = result_target
        if mapping_keys:
            cfg["mapping_keys"] = mapping_keys
    elif command_code == "dropDataset":
        dataset_id = str(
            st.session_state.get(f"suite_add_test_drop_dataset_id_{dialog_nonce}") or ""
        ).strip()
        if not dataset_id:
            return None, "Il campo Dataset e' obbligatorio."
        cfg = {
            "commandCode": "dropDataset",
            "commandType": "action",
            "dataset_id": dataset_id,
        }
    elif command_code == "cleanDataset":
        dataset_id = str(
            st.session_state.get(f"suite_add_test_clean_dataset_id_{dialog_nonce}") or ""
        ).strip()
        if not dataset_id:
            return None, "Il campo Dataset e' obbligatorio."
        cfg = {
            "commandCode": "cleanDataset",
            "commandType": "action",
            "dataset_id": dataset_id,
        }
    elif command_code in TEST_ASSERT_COMMAND_CODES:
        cfg = {
            "commandCode": command_code,
            "commandType": "assert",
        }
        actual, parse_error = _parse_json_or_ref_input(
            st.session_state.get(f"suite_add_test_assert_actual_{dialog_nonce}")
        )
        if parse_error:
            return None, parse_error
        expected, expected_error = _parse_json_or_ref_input(
            st.session_state.get(f"suite_add_test_assert_expected_{dialog_nonce}")
        )
        if expected_error:
            return None, expected_error
        error_message = str(
            st.session_state.get(f"suite_add_test_assert_error_message_{dialog_nonce}") or ""
        ).strip()
        if actual is not None:
            cfg["actual"] = actual
        if expected is not None:
            cfg["expected"] = expected
        if error_message:
            cfg["error_message"] = error_message
        if command_code in {"jsonContains", "jsonArrayContains", "jsonArrayEquals"}:
            expected_json_array_id = str(
                st.session_state.get(f"suite_add_test_assert_expected_json_array_id_{dialog_nonce}") or ""
            ).strip()
            if command_code in {"jsonArrayContains", "jsonArrayEquals"} and not expected_json_array_id:
                return None, "Il campo Expected json-array e' obbligatorio."
            if expected_json_array_id:
                cfg["expected_json_array_id"] = expected_json_array_id
            compare_keys = _parse_csv_tokens(
                st.session_state.get(f"suite_add_test_assert_compare_keys_{dialog_nonce}")
            )
            if command_code in {"jsonArrayContains", "jsonArrayEquals"} and not compare_keys:
                return None, "Il campo Compare keys e' obbligatorio."
            if compare_keys:
                cfg["compare_keys"] = compare_keys
    else:
        return None, f"Command type non supportato: {command_ui_code}"

    return {
        "description": description,
        "operation_type": command_code,
        "configuration_json": cfg,
    }, None


def _initialize_hook_command_form(
    dialog_nonce: int,
    command_item: dict,
    brokers: list[dict],
    *,
    default_context: str,
    key_prefix: str,
):
    initialized_key = _command_form_key(key_prefix, dialog_nonce, "initialized")
    if st.session_state.get(initialized_key):
        return

    configuration_json = _safe_dict(command_item.get("configuration_json") or {})
    command_code = _normalize_command_code(configuration_json)
    st.session_state[_command_form_key(key_prefix, dialog_nonce, "description")] = str(
        command_item.get("description") or ""
    )
    st.session_state[_command_form_key(key_prefix, dialog_nonce, "command_type")] = command_code

    if command_code == "initConstant":
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "init_constant_name")] = str(
            configuration_json.get("name") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "init_constant_context")] = default_context
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "init_constant_source_type")] = str(
            configuration_json.get("sourceType") or "raw"
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "init_constant_value")] = _stringify_form_value(
            configuration_json.get("value")
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "init_constant_json_array_id")] = str(
            configuration_json.get("json_array_id") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "init_constant_dataset_id")] = str(
            configuration_json.get("dataset_id") or ""
        )
        queue_id = str(configuration_json.get("queue_id") or "")
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "init_constant_queue_id")] = queue_id
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "init_constant_broker_id")] = (
            _find_broker_id_for_queue_id(queue_id, brokers)
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "init_constant_retry")] = _safe_int(
            configuration_json.get("retry"),
            3,
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "init_constant_wait_time_seconds")] = _safe_int(
            configuration_json.get("wait_time_seconds"),
            20,
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "init_constant_max_messages")] = _safe_int(
            configuration_json.get("max_messages"),
            1000,
        )
    elif command_code == "deleteConstant":
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "delete_constant_name")] = str(
            configuration_json.get("name") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "delete_constant_context")] = default_context
    elif command_code == "saveTable":
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "save_table_name")] = str(
            configuration_json.get("table_name") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "save_table_source")] = str(
            configuration_json.get("source") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "save_table_result_target")] = str(
            configuration_json.get("result_target") or ""
        )
    elif command_code == "dropTable":
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "drop_table_name")] = str(
            configuration_json.get("table_name") or ""
        )
    elif command_code == "cleanTable":
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "clean_table_name")] = str(
            configuration_json.get("table_name") or ""
        )
    elif command_code == "exportDataset":
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "export_dataset_connection_id")] = str(
            configuration_json.get("connection_id") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "export_dataset_table_name")] = str(
            configuration_json.get("table_name") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "export_dataset_source")] = str(
            configuration_json.get("source") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "export_dataset_mode")] = str(
            configuration_json.get("mode") or "append"
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "export_dataset_mapping_keys")] = _csv_from_value(
            configuration_json.get("mapping_keys")
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "export_dataset_dataset_id")] = str(
            configuration_json.get("dataset_id") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "export_dataset_dataset_description")] = str(
            configuration_json.get("dataset_description") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "export_dataset_result_target")] = str(
            configuration_json.get("result_target") or ""
        )
    elif command_code == "dropDataset":
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "drop_dataset_id")] = str(
            configuration_json.get("dataset_id") or ""
        )
    elif command_code == "cleanDataset":
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "clean_dataset_id")] = str(
            configuration_json.get("dataset_id") or ""
        )

    st.session_state[initialized_key] = True


def _initialize_test_command_form(
    dialog_nonce: int,
    command_item: dict,
    brokers: list[dict],
    *,
    key_prefix: str,
):
    initialized_key = _command_form_key(key_prefix, dialog_nonce, "initialized")
    if st.session_state.get(initialized_key):
        return

    configuration_json = _safe_dict(command_item.get("configuration_json") or {})
    command_code = _normalize_command_code(configuration_json)
    st.session_state[_command_form_key(key_prefix, dialog_nonce, "description")] = str(
        command_item.get("description") or ""
    )
    st.session_state[_command_form_key(key_prefix, dialog_nonce, "command_type")] = command_code

    if command_code == "initConstant":
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "init_constant_name")] = str(
            configuration_json.get("name") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "init_constant_context")] = "local"
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "init_constant_source_type")] = str(
            configuration_json.get("sourceType") or "raw"
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "init_constant_value")] = _stringify_form_value(
            configuration_json.get("value")
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "init_constant_json_array_id")] = str(
            configuration_json.get("json_array_id") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "init_constant_dataset_id")] = str(
            configuration_json.get("dataset_id") or ""
        )
        queue_id = str(configuration_json.get("queue_id") or "")
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "init_constant_queue_id")] = queue_id
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "init_constant_broker_id")] = (
            _find_broker_id_for_queue_id(queue_id, brokers)
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "init_constant_retry")] = _safe_int(
            configuration_json.get("retry"),
            3,
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "init_constant_wait_time_seconds")] = _safe_int(
            configuration_json.get("wait_time_seconds"),
            20,
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "init_constant_max_messages")] = _safe_int(
            configuration_json.get("max_messages"),
            1000,
        )
    elif command_code == "sendMessageQueue":
        queue_id = str(configuration_json.get("queue_id") or "")
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "send_message_broker_id")] = (
            _find_broker_id_for_queue_id(queue_id, brokers)
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "send_message_queue_id")] = queue_id
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "send_message_source")] = str(
            configuration_json.get("source") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "send_message_template_id")] = str(
            configuration_json.get("template_id") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "send_message_template_params")] = (
            _stringify_form_value(configuration_json.get("template_params"))
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "send_message_result_target")] = str(
            configuration_json.get("result_target") or ""
        )
    elif command_code == "saveTable":
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "save_table_name")] = str(
            configuration_json.get("table_name") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "save_table_source")] = str(
            configuration_json.get("source") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "save_table_result_target")] = str(
            configuration_json.get("result_target") or ""
        )
    elif command_code == "dropTable":
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "drop_table_name")] = str(
            configuration_json.get("table_name") or ""
        )
    elif command_code == "cleanTable":
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "clean_table_name")] = str(
            configuration_json.get("table_name") or ""
        )
    elif command_code == "exportDataset":
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "export_dataset_connection_id")] = str(
            configuration_json.get("connection_id") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "export_dataset_table_name")] = str(
            configuration_json.get("table_name") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "export_dataset_source")] = str(
            configuration_json.get("source") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "export_dataset_mode")] = str(
            configuration_json.get("mode") or "append"
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "export_dataset_mapping_keys")] = _csv_from_value(
            configuration_json.get("mapping_keys")
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "export_dataset_dataset_id")] = str(
            configuration_json.get("dataset_id") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "export_dataset_dataset_description")] = str(
            configuration_json.get("dataset_description") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "export_dataset_result_target")] = str(
            configuration_json.get("result_target") or ""
        )
    elif command_code == "dropDataset":
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "drop_dataset_id")] = str(
            configuration_json.get("dataset_id") or ""
        )
    elif command_code == "cleanDataset":
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "clean_dataset_id")] = str(
            configuration_json.get("dataset_id") or ""
        )
    elif command_code in TEST_ASSERT_COMMAND_CODES:
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "assert_error_message")] = str(
            configuration_json.get("error_message") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "assert_actual")] = _stringify_form_value(
            configuration_json.get("actual")
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "assert_expected")] = _stringify_form_value(
            configuration_json.get("expected")
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "assert_expected_json_array_id")] = str(
            configuration_json.get("expected_json_array_id") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "assert_compare_keys")] = _csv_from_value(
            configuration_json.get("compare_keys")
        )

    st.session_state[initialized_key] = True


def _render_hook_command_form(
    dialog_nonce: int,
    command_group: str,
    json_arrays: list[dict],
    datasources: list[dict],
    brokers: list[dict],
    connections: list[dict],
    draft: dict,
    item: dict,
    *,
    stop_before_index: int | None,
    default_context: str,
    key_prefix: str,
) -> str:
    allowed_command_codes = HOOK_CONTEXT_COMMAND_CODES if command_group == "context" else HOOK_ACTION_COMMAND_CODES
    command_type_key = _command_form_key(key_prefix, dialog_nonce, "command_type")
    current_command_code = str(st.session_state.get(command_type_key) or "").strip()
    if current_command_code not in allowed_command_codes and allowed_command_codes:
        st.session_state[command_type_key] = allowed_command_codes[0]

    st.text_input("Description", key=_command_form_key(key_prefix, dialog_nonce, "description"))
    command_code = st.selectbox(
        "Command type",
        options=allowed_command_codes,
        format_func=lambda code: HOOK_COMMAND_LABELS.get(str(code), str(code)),
        key=command_type_key,
    )

    if command_code == "initConstant":
        st.text_input("Name", key=_command_form_key(key_prefix, dialog_nonce, "init_constant_name"), placeholder="rows")
        context_key = _command_form_key(key_prefix, dialog_nonce, "init_constant_context")
        st.session_state[context_key] = default_context
        source_type_key = _command_form_key(key_prefix, dialog_nonce, "init_constant_source_type")
        current_source_type = str(st.session_state.get(source_type_key) or "").strip()
        if current_source_type not in CONSTANT_SOURCE_OPTIONS:
            st.session_state[source_type_key] = CONSTANT_SOURCE_OPTIONS[0]
        source_type = st.selectbox("Source type", options=CONSTANT_SOURCE_OPTIONS, key=source_type_key)
        if source_type in {"raw", "json"}:
            st.text_area(
                "Value",
                key=_command_form_key(key_prefix, dialog_nonce, "init_constant_value"),
                height=180,
                help="Per `raw` puoi inserire testo o JSON. Per `json` inserisci JSON valido.",
            )
        elif source_type == "jsonArray":
            json_array_ids = [str(item.get("id")) for item in json_arrays if item.get("id")]
            st.selectbox(
                "Json array",
                options=json_array_ids or [""],
                format_func=lambda item_id: _format_lookup_label(
                    next((item for item in json_arrays if str(item.get("id")) == str(item_id)), {})
                ) if item_id else "Nessun json-array disponibile",
                key=_command_form_key(key_prefix, dialog_nonce, "init_constant_json_array_id"),
                disabled=not bool(json_array_ids),
            )
        elif source_type == "dataset":
            dataset_ids = [str(item.get("id")) for item in datasources if item.get("id")]
            st.selectbox(
                "Dataset",
                options=dataset_ids or [""],
                format_func=lambda item_id: _format_lookup_label(
                    next((item for item in datasources if str(item.get("id")) == str(item_id)), {})
                ) if item_id else "Nessun dataset disponibile",
                key=_command_form_key(key_prefix, dialog_nonce, "init_constant_dataset_id"),
                disabled=not bool(dataset_ids),
            )
        elif source_type == "sqsQueue":
            broker_ids = [str(item.get("id")) for item in brokers if item.get("id")]
            broker_key = _command_form_key(key_prefix, dialog_nonce, "init_constant_broker_id")
            current_broker_id = str(st.session_state.get(broker_key) or "").strip()
            if current_broker_id not in broker_ids and broker_ids:
                st.session_state[broker_key] = broker_ids[0]
            selected_broker_id = st.selectbox(
                "Broker",
                options=broker_ids or [""],
                format_func=lambda item_id: _format_lookup_label(
                    next((item for item in brokers if str(item.get("id")) == str(item_id)), {})
                ) if item_id else "Nessun broker disponibile",
                key=broker_key,
                disabled=not bool(broker_ids),
            )
            queues = load_test_editor_queues_for_broker(selected_broker_id, force=False) if selected_broker_id else []
            queue_ids = [str(item.get("id")) for item in queues if item.get("id")]
            queue_key = _command_form_key(key_prefix, dialog_nonce, "init_constant_queue_id")
            current_queue_id = str(st.session_state.get(queue_key) or "").strip()
            if current_queue_id not in queue_ids and queue_ids:
                st.session_state[queue_key] = queue_ids[0]
            st.selectbox(
                "Queue",
                options=queue_ids or [""],
                format_func=lambda item_id: _format_lookup_label(
                    next((item for item in queues if str(item.get("id")) == str(item_id)), {})
                ) if item_id else "Nessuna queue disponibile",
                key=queue_key,
                disabled=not bool(queue_ids),
            )
            st.number_input("Retry", min_value=1, value=3, key=_command_form_key(key_prefix, dialog_nonce, "init_constant_retry"))
            st.number_input("Wait time seconds", min_value=0, value=20, key=_command_form_key(key_prefix, dialog_nonce, "init_constant_wait_time_seconds"))
            st.number_input("Max messages", min_value=1, value=1000, key=_command_form_key(key_prefix, dialog_nonce, "init_constant_max_messages"))
    elif command_code == "deleteConstant":
        st.text_input("Name", key=_command_form_key(key_prefix, dialog_nonce, "delete_constant_name"), placeholder="rows")
        delete_context_key = _command_form_key(key_prefix, dialog_nonce, "delete_constant_context")
        st.session_state[delete_context_key] = default_context
    elif command_code == "saveTable":
        st.text_input("Table name", key=_command_form_key(key_prefix, dialog_nonce, "save_table_name"))
        _render_source_constant_select(
            label="Source constant",
            key=_command_form_key(key_prefix, dialog_nonce, "save_table_source"),
            options=_resolve_available_source_constants(
                draft,
                item,
                command_code=command_code,
                stop_before_index=stop_before_index,
            ),
            help_text="Costanti visibili e compatibili nel punto corrente.",
        )
        st.text_input("Result target (optional)", key=_command_form_key(key_prefix, dialog_nonce, "save_table_result_target"), placeholder="$.result.commands.saveTable")
    elif command_code == "dropTable":
        st.text_input("Table name", key=_command_form_key(key_prefix, dialog_nonce, "drop_table_name"))
    elif command_code == "cleanTable":
        st.text_input("Table name", key=_command_form_key(key_prefix, dialog_nonce, "clean_table_name"))
    elif command_code == "exportDataset":
        connection_ids = [str(item.get("id")) for item in connections if item.get("id")]
        dataset_ids = [str(item.get("id")) for item in datasources if item.get("id")]
        st.selectbox(
            "Connection",
            options=connection_ids or [""],
            format_func=lambda item_id: _format_lookup_label(next((item for item in connections if str(item.get("id")) == str(item_id)), {})) if item_id else "Nessuna connection disponibile",
            key=_command_form_key(key_prefix, dialog_nonce, "export_dataset_connection_id"),
            disabled=not bool(connection_ids),
        )
        st.text_input("Table name", key=_command_form_key(key_prefix, dialog_nonce, "export_dataset_table_name"))
        _render_source_constant_select(
            label="Source constant",
            key=_command_form_key(key_prefix, dialog_nonce, "export_dataset_source"),
            options=_resolve_available_source_constants(
                draft,
                item,
                command_code=command_code,
                stop_before_index=stop_before_index,
            ),
            help_text="Costanti visibili e compatibili nel punto corrente.",
        )
        st.selectbox("Mode", options=EXPORT_DATASET_MODE_OPTIONS, key=_command_form_key(key_prefix, dialog_nonce, "export_dataset_mode"))
        st.text_input("Mapping keys (optional)", key=_command_form_key(key_prefix, dialog_nonce, "export_dataset_mapping_keys"), placeholder="id, code")
        st.selectbox(
            "Existing dataset (optional)",
            options=[""] + dataset_ids,
            format_func=lambda item_id: _format_lookup_label(next((item for item in datasources if str(item.get("id")) == str(item_id)), {})) if item_id else "Create new dataset",
            key=_command_form_key(key_prefix, dialog_nonce, "export_dataset_dataset_id"),
        )
        st.text_input("Dataset description (optional)", key=_command_form_key(key_prefix, dialog_nonce, "export_dataset_dataset_description"))
        st.text_input("Result target (optional)", key=_command_form_key(key_prefix, dialog_nonce, "export_dataset_result_target"), placeholder="$.result.commands.exportDataset")
    elif command_code == "dropDataset":
        dataset_ids = [str(item.get("id")) for item in datasources if item.get("id")]
        st.selectbox(
            "Dataset",
            options=dataset_ids or [""],
            format_func=lambda item_id: _format_lookup_label(next((item for item in datasources if str(item.get("id")) == str(item_id)), {})) if item_id else "Nessun dataset disponibile",
            key=_command_form_key(key_prefix, dialog_nonce, "drop_dataset_id"),
            disabled=not bool(dataset_ids),
        )
    elif command_code == "cleanDataset":
        dataset_ids = [str(item.get("id")) for item in datasources if item.get("id")]
        st.selectbox(
            "Dataset",
            options=dataset_ids or [""],
            format_func=lambda item_id: _format_lookup_label(next((item for item in datasources if str(item.get("id")) == str(item_id)), {})) if item_id else "Nessun dataset disponibile",
            key=_command_form_key(key_prefix, dialog_nonce, "clean_dataset_id"),
            disabled=not bool(dataset_ids),
        )
    return command_code


def _render_test_command_form(
    dialog_nonce: int,
    command_group: str,
    json_arrays: list[dict],
    datasources: list[dict],
    brokers: list[dict],
    connections: list[dict],
    draft: dict,
    item: dict,
    *,
    stop_before_index: int | None,
    key_prefix: str,
) -> str:
    if command_group == "constant":
        command_options = TEST_CONSTANT_COMMAND_CODES
    elif command_group == "assert":
        command_options = TEST_ASSERT_COMMAND_CODES
    else:
        command_options = [item[0] for item in TEST_ACTION_COMMAND_OPTIONS]

    command_type_key = _command_form_key(key_prefix, dialog_nonce, "command_type")
    current_command_ui_code = str(st.session_state.get(command_type_key) or "").strip()
    if current_command_ui_code not in command_options and command_options:
        st.session_state[command_type_key] = command_options[0]

    st.text_input("Description", key=_command_form_key(key_prefix, dialog_nonce, "description"))
    command_ui_code = st.selectbox(
        "Command type",
        options=command_options,
        format_func=lambda code: dict(TEST_ACTION_COMMAND_OPTIONS).get(str(code), str(code)) if command_group == "action" else str(code),
        key=command_type_key,
    )
    command_code = TEST_ACTION_COMMAND_MAPPING.get(command_ui_code, command_ui_code)

    if command_code == "initConstant":
        st.text_input("Name", key=_command_form_key(key_prefix, dialog_nonce, "init_constant_name"), placeholder="rows")
        context_key = _command_form_key(key_prefix, dialog_nonce, "init_constant_context")
        st.session_state[context_key] = "local"
        source_type_key = _command_form_key(key_prefix, dialog_nonce, "init_constant_source_type")
        current_source_type = str(st.session_state.get(source_type_key) or "").strip()
        if current_source_type not in CONSTANT_SOURCE_OPTIONS:
            st.session_state[source_type_key] = CONSTANT_SOURCE_OPTIONS[0]
        source_type = st.selectbox("Source type", options=CONSTANT_SOURCE_OPTIONS, key=source_type_key)
        if source_type in {"raw", "json"}:
            st.text_area("Value", key=_command_form_key(key_prefix, dialog_nonce, "init_constant_value"), height=180, help="Per `raw` puoi inserire testo o JSON. Per `json` inserisci JSON valido.")
        elif source_type == "jsonArray":
            json_array_ids = [str(item.get("id")) for item in json_arrays if item.get("id")]
            st.selectbox(
                "Json array",
                options=json_array_ids or [""],
                format_func=lambda item_id: _format_lookup_label(next((item for item in json_arrays if str(item.get("id")) == str(item_id)), {})) if item_id else "Nessun json-array disponibile",
                key=_command_form_key(key_prefix, dialog_nonce, "init_constant_json_array_id"),
                disabled=not bool(json_array_ids),
            )
        elif source_type == "dataset":
            dataset_ids = [str(item.get("id")) for item in datasources if item.get("id")]
            st.selectbox(
                "Dataset",
                options=dataset_ids or [""],
                format_func=lambda item_id: _format_lookup_label(next((item for item in datasources if str(item.get("id")) == str(item_id)), {})) if item_id else "Nessun dataset disponibile",
                key=_command_form_key(key_prefix, dialog_nonce, "init_constant_dataset_id"),
                disabled=not bool(dataset_ids),
            )
        elif source_type == "sqsQueue":
            broker_ids = [str(item.get("id")) for item in brokers if item.get("id")]
            broker_key = _command_form_key(key_prefix, dialog_nonce, "init_constant_broker_id")
            current_broker_id = str(st.session_state.get(broker_key) or "").strip()
            if current_broker_id not in broker_ids and broker_ids:
                st.session_state[broker_key] = broker_ids[0]
            selected_broker_id = st.selectbox(
                "Broker",
                options=broker_ids or [""],
                format_func=lambda item_id: _format_lookup_label(next((item for item in brokers if str(item.get("id")) == str(item_id)), {})) if item_id else "Nessun broker disponibile",
                key=broker_key,
                disabled=not bool(broker_ids),
            )
            queues = load_test_editor_queues_for_broker(selected_broker_id, force=False) if selected_broker_id else []
            queue_ids = [str(item.get("id")) for item in queues if item.get("id")]
            queue_key = _command_form_key(key_prefix, dialog_nonce, "init_constant_queue_id")
            current_queue_id = str(st.session_state.get(queue_key) or "").strip()
            if current_queue_id not in queue_ids and queue_ids:
                st.session_state[queue_key] = queue_ids[0]
            st.selectbox(
                "Queue",
                options=queue_ids or [""],
                format_func=lambda item_id: _format_lookup_label(next((item for item in queues if str(item.get("id")) == str(item_id)), {})) if item_id else "Nessuna queue disponibile",
                key=queue_key,
                disabled=not bool(queue_ids),
            )
            st.number_input("Retry", min_value=1, value=3, key=_command_form_key(key_prefix, dialog_nonce, "init_constant_retry"))
            st.number_input("Wait time seconds", min_value=0, value=20, key=_command_form_key(key_prefix, dialog_nonce, "init_constant_wait_time_seconds"))
            st.number_input("Max messages", min_value=1, value=1000, key=_command_form_key(key_prefix, dialog_nonce, "init_constant_max_messages"))
    elif command_code == "sendMessageQueue":
        broker_ids = [str(item.get("id")) for item in brokers if item.get("id")]
        broker_key = _command_form_key(key_prefix, dialog_nonce, "send_message_broker_id")
        current_broker_id = str(st.session_state.get(broker_key) or "").strip()
        if current_broker_id not in broker_ids and broker_ids:
            st.session_state[broker_key] = broker_ids[0]
        selected_broker_id = st.selectbox(
            "Broker",
            options=broker_ids or [""],
            format_func=lambda item_id: _format_lookup_label(next((item for item in brokers if str(item.get("id")) == str(item_id)), {})) if item_id else "Nessun broker disponibile",
            key=broker_key,
            disabled=not bool(broker_ids),
        )
        queues = load_test_editor_queues_for_broker(selected_broker_id, force=False) if selected_broker_id else []
        queue_ids = [str(item.get("id")) for item in queues if item.get("id")]
        queue_key = _command_form_key(key_prefix, dialog_nonce, "send_message_queue_id")
        current_queue_id = str(st.session_state.get(queue_key) or "").strip()
        if current_queue_id not in queue_ids and queue_ids:
            st.session_state[queue_key] = queue_ids[0]
        st.selectbox(
            "Queue",
            options=queue_ids or [""],
            format_func=lambda item_id: _format_lookup_label(next((item for item in queues if str(item.get("id")) == str(item_id)), {})) if item_id else "Nessuna queue disponibile",
            key=queue_key,
            disabled=not bool(queue_ids),
        )
        _render_source_constant_select(
            label="Source constant",
            key=_command_form_key(key_prefix, dialog_nonce, "send_message_source"),
            options=_resolve_available_source_constants(
                draft,
                item,
                command_code=command_code,
                stop_before_index=stop_before_index,
            ),
            help_text="Costanti visibili e compatibili nel punto corrente.",
        )
        st.text_input("Template id (optional)", key=_command_form_key(key_prefix, dialog_nonce, "send_message_template_id"))
        st.text_area("Template params (optional)", key=_command_form_key(key_prefix, dialog_nonce, "send_message_template_params"), height=120)
        st.text_input("Result target (optional)", key=_command_form_key(key_prefix, dialog_nonce, "send_message_result_target"), placeholder="$.result.commands.sendMessageQueue")
    elif command_code == "saveTable":
        st.text_input("Table name", key=_command_form_key(key_prefix, dialog_nonce, "save_table_name"))
        _render_source_constant_select(
            label="Source constant",
            key=_command_form_key(key_prefix, dialog_nonce, "save_table_source"),
            options=_resolve_available_source_constants(
                draft,
                item,
                command_code=command_code,
                stop_before_index=stop_before_index,
            ),
            help_text="Costanti visibili e compatibili nel punto corrente.",
        )
        st.text_input("Result target (optional)", key=_command_form_key(key_prefix, dialog_nonce, "save_table_result_target"), placeholder="$.result.commands.saveTable")
    elif command_code == "dropTable":
        st.text_input("Table name", key=_command_form_key(key_prefix, dialog_nonce, "drop_table_name"))
    elif command_code == "cleanTable":
        st.text_input("Table name", key=_command_form_key(key_prefix, dialog_nonce, "clean_table_name"))
    elif command_code == "exportDataset":
        connection_ids = [str(item.get("id")) for item in connections if item.get("id")]
        dataset_ids = [str(item.get("id")) for item in datasources if item.get("id")]
        st.selectbox(
            "Connection",
            options=connection_ids or [""],
            format_func=lambda item_id: _format_lookup_label(next((item for item in connections if str(item.get("id")) == str(item_id)), {})) if item_id else "Nessuna connection disponibile",
            key=_command_form_key(key_prefix, dialog_nonce, "export_dataset_connection_id"),
            disabled=not bool(connection_ids),
        )
        st.text_input("Table name", key=_command_form_key(key_prefix, dialog_nonce, "export_dataset_table_name"))
        _render_source_constant_select(
            label="Source constant",
            key=_command_form_key(key_prefix, dialog_nonce, "export_dataset_source"),
            options=_resolve_available_source_constants(
                draft,
                item,
                command_code=command_code,
                stop_before_index=stop_before_index,
            ),
            help_text="Costanti visibili e compatibili nel punto corrente.",
        )
        st.selectbox("Mode", options=EXPORT_DATASET_MODE_OPTIONS, key=_command_form_key(key_prefix, dialog_nonce, "export_dataset_mode"))
        st.text_input("Mapping keys (optional)", key=_command_form_key(key_prefix, dialog_nonce, "export_dataset_mapping_keys"), placeholder="id, code")
        st.selectbox(
            "Existing dataset (optional)",
            options=[""] + dataset_ids,
            format_func=lambda item_id: _format_lookup_label(next((item for item in datasources if str(item.get("id")) == str(item_id)), {})) if item_id else "Create new dataset",
            key=_command_form_key(key_prefix, dialog_nonce, "export_dataset_dataset_id"),
        )
        st.text_input("Dataset description (optional)", key=_command_form_key(key_prefix, dialog_nonce, "export_dataset_dataset_description"))
        st.text_input("Result target (optional)", key=_command_form_key(key_prefix, dialog_nonce, "export_dataset_result_target"), placeholder="$.result.commands.exportDataset")
    elif command_code == "dropDataset":
        dataset_ids = [str(item.get("id")) for item in datasources if item.get("id")]
        st.selectbox(
            "Dataset",
            options=dataset_ids or [""],
            format_func=lambda item_id: _format_lookup_label(next((item for item in datasources if str(item.get("id")) == str(item_id)), {})) if item_id else "Nessun dataset disponibile",
            key=_command_form_key(key_prefix, dialog_nonce, "drop_dataset_id"),
            disabled=not bool(dataset_ids),
        )
    elif command_code == "cleanDataset":
        dataset_ids = [str(item.get("id")) for item in datasources if item.get("id")]
        st.selectbox(
            "Dataset",
            options=dataset_ids or [""],
            format_func=lambda item_id: _format_lookup_label(next((item for item in datasources if str(item.get("id")) == str(item_id)), {})) if item_id else "Nessun dataset disponibile",
            key=_command_form_key(key_prefix, dialog_nonce, "clean_dataset_id"),
            disabled=not bool(dataset_ids),
        )
    elif command_code in TEST_ASSERT_COMMAND_CODES:
        st.text_input("Error message (optional)", key=_command_form_key(key_prefix, dialog_nonce, "assert_error_message"))
        st.text_area("Actual (optional)", key=_command_form_key(key_prefix, dialog_nonce, "assert_actual"), height=120, help="JSON valido o path tipo `$.local.constants.rows`.")
        if command_code == "jsonEquals":
            st.text_area("Expected", key=_command_form_key(key_prefix, dialog_nonce, "assert_expected"), height=120, help="JSON valido o path tipo `$.runEnvelope.event.payload`.")
        if command_code in {"jsonContains", "jsonArrayContains", "jsonArrayEquals"}:
            json_array_ids = [str(item.get("id")) for item in json_arrays if item.get("id")]
            st.selectbox(
                "Expected json-array",
                options=[""] + json_array_ids,
                format_func=lambda item_id: _format_lookup_label(next((item for item in json_arrays if str(item.get("id")) == str(item_id)), {})) if item_id else "Nessun json-array selezionato",
                key=_command_form_key(key_prefix, dialog_nonce, "assert_expected_json_array_id"),
            )
            st.text_input("Compare keys (optional)", key=_command_form_key(key_prefix, dialog_nonce, "assert_compare_keys"), placeholder="id, code")

    return command_ui_code


def _build_hook_command_draft_with_prefix(
    dialog_nonce: int,
    command_code: str,
    *,
    key_prefix: str,
) -> tuple[dict | None, str | None]:
    description = str(st.session_state.get(_command_form_key(key_prefix, dialog_nonce, "description")) or "").strip()
    if not description:
        return None, "Il campo Description e' obbligatorio."

    original_keys = []
    field_mappings = [
        ("description", f"suite_add_hook_command_description_{dialog_nonce}"),
        ("command_type", f"suite_add_hook_command_type_{dialog_nonce}"),
        ("init_constant_name", f"suite_add_hook_init_constant_name_{dialog_nonce}"),
        ("init_constant_context", f"suite_add_hook_init_constant_context_{dialog_nonce}"),
        ("init_constant_source_type", f"suite_add_hook_init_constant_source_type_{dialog_nonce}"),
        ("init_constant_value", f"suite_add_hook_init_constant_value_{dialog_nonce}"),
        ("init_constant_json_array_id", f"suite_add_hook_init_constant_json_array_id_{dialog_nonce}"),
        ("init_constant_dataset_id", f"suite_add_hook_init_constant_dataset_id_{dialog_nonce}"),
        ("init_constant_queue_id", f"suite_add_hook_init_constant_queue_id_{dialog_nonce}"),
        ("init_constant_retry", f"suite_add_hook_init_constant_retry_{dialog_nonce}"),
        ("init_constant_wait_time_seconds", f"suite_add_hook_init_constant_wait_time_seconds_{dialog_nonce}"),
        ("init_constant_max_messages", f"suite_add_hook_init_constant_max_messages_{dialog_nonce}"),
        ("delete_constant_name", f"suite_add_hook_delete_constant_name_{dialog_nonce}"),
        ("delete_constant_context", f"suite_add_hook_delete_constant_context_{dialog_nonce}"),
        ("save_table_name", f"suite_add_hook_save_table_name_{dialog_nonce}"),
        ("save_table_source", f"suite_add_hook_save_table_source_{dialog_nonce}"),
        ("save_table_result_target", f"suite_add_hook_save_table_result_target_{dialog_nonce}"),
        ("drop_table_name", f"suite_add_hook_drop_table_name_{dialog_nonce}"),
        ("clean_table_name", f"suite_add_hook_clean_table_name_{dialog_nonce}"),
        ("export_dataset_connection_id", f"suite_add_hook_export_dataset_connection_id_{dialog_nonce}"),
        ("export_dataset_table_name", f"suite_add_hook_export_dataset_table_name_{dialog_nonce}"),
        ("export_dataset_source", f"suite_add_hook_export_dataset_source_{dialog_nonce}"),
        ("export_dataset_mode", f"suite_add_hook_export_dataset_mode_{dialog_nonce}"),
        ("export_dataset_mapping_keys", f"suite_add_hook_export_dataset_mapping_keys_{dialog_nonce}"),
        ("export_dataset_dataset_id", f"suite_add_hook_export_dataset_dataset_id_{dialog_nonce}"),
        ("export_dataset_dataset_description", f"suite_add_hook_export_dataset_dataset_description_{dialog_nonce}"),
        ("export_dataset_result_target", f"suite_add_hook_export_dataset_result_target_{dialog_nonce}"),
        ("drop_dataset_id", f"suite_add_hook_drop_dataset_id_{dialog_nonce}"),
        ("clean_dataset_id", f"suite_add_hook_clean_dataset_id_{dialog_nonce}"),
    ]
    try:
        for source_suffix, legacy_key in field_mappings:
            original_keys.append((legacy_key, st.session_state.get(legacy_key)))
            value = st.session_state.get(_command_form_key(key_prefix, dialog_nonce, source_suffix))
            if value is None:
                st.session_state.pop(legacy_key, None)
            else:
                st.session_state[legacy_key] = value
        return _build_hook_command_draft(dialog_nonce, command_code)
    finally:
        for legacy_key, original_value in original_keys:
            if original_value is None and legacy_key in st.session_state:
                st.session_state.pop(legacy_key, None)
            elif original_value is not None:
                st.session_state[legacy_key] = original_value


def _build_test_command_draft_with_prefix(
    dialog_nonce: int,
    command_ui_code: str,
    *,
    key_prefix: str,
) -> tuple[dict | None, str | None]:
    description = str(st.session_state.get(_command_form_key(key_prefix, dialog_nonce, "description")) or "").strip()
    if not description:
        return None, "Il campo Description e' obbligatorio."

    original_keys = []
    field_mappings = [
        ("description", f"suite_add_test_command_description_{dialog_nonce}"),
        ("command_type", f"suite_add_test_command_type_{dialog_nonce}"),
        ("init_constant_name", f"suite_add_test_init_constant_name_{dialog_nonce}"),
        ("init_constant_context", f"suite_add_test_init_constant_context_{dialog_nonce}"),
        ("init_constant_source_type", f"suite_add_test_init_constant_source_type_{dialog_nonce}"),
        ("init_constant_value", f"suite_add_test_init_constant_value_{dialog_nonce}"),
        ("init_constant_json_array_id", f"suite_add_test_init_constant_json_array_id_{dialog_nonce}"),
        ("init_constant_dataset_id", f"suite_add_test_init_constant_dataset_id_{dialog_nonce}"),
        ("init_constant_broker_id", f"suite_add_test_init_constant_broker_id_{dialog_nonce}"),
        ("init_constant_queue_id", f"suite_add_test_init_constant_queue_id_{dialog_nonce}"),
        ("init_constant_retry", f"suite_add_test_init_constant_retry_{dialog_nonce}"),
        ("init_constant_wait_time_seconds", f"suite_add_test_init_constant_wait_time_seconds_{dialog_nonce}"),
        ("init_constant_max_messages", f"suite_add_test_init_constant_max_messages_{dialog_nonce}"),
        ("send_message_broker_id", f"suite_add_test_send_message_broker_id_{dialog_nonce}"),
        ("send_message_queue_id", f"suite_add_test_send_message_queue_id_{dialog_nonce}"),
        ("send_message_source", f"suite_add_test_send_message_source_{dialog_nonce}"),
        ("send_message_template_id", f"suite_add_test_send_message_template_id_{dialog_nonce}"),
        ("send_message_template_params", f"suite_add_test_send_message_template_params_{dialog_nonce}"),
        ("send_message_result_target", f"suite_add_test_send_message_result_target_{dialog_nonce}"),
        ("save_table_name", f"suite_add_test_save_table_name_{dialog_nonce}"),
        ("save_table_source", f"suite_add_test_save_table_source_{dialog_nonce}"),
        ("save_table_result_target", f"suite_add_test_save_table_result_target_{dialog_nonce}"),
        ("drop_table_name", f"suite_add_test_drop_table_name_{dialog_nonce}"),
        ("clean_table_name", f"suite_add_test_clean_table_name_{dialog_nonce}"),
        ("export_dataset_connection_id", f"suite_add_test_export_dataset_connection_id_{dialog_nonce}"),
        ("export_dataset_table_name", f"suite_add_test_export_dataset_table_name_{dialog_nonce}"),
        ("export_dataset_source", f"suite_add_test_export_dataset_source_{dialog_nonce}"),
        ("export_dataset_mode", f"suite_add_test_export_dataset_mode_{dialog_nonce}"),
        ("export_dataset_mapping_keys", f"suite_add_test_export_dataset_mapping_keys_{dialog_nonce}"),
        ("export_dataset_dataset_id", f"suite_add_test_export_dataset_dataset_id_{dialog_nonce}"),
        ("export_dataset_dataset_description", f"suite_add_test_export_dataset_dataset_description_{dialog_nonce}"),
        ("export_dataset_result_target", f"suite_add_test_export_dataset_result_target_{dialog_nonce}"),
        ("drop_dataset_id", f"suite_add_test_drop_dataset_id_{dialog_nonce}"),
        ("clean_dataset_id", f"suite_add_test_clean_dataset_id_{dialog_nonce}"),
        ("assert_error_message", f"suite_add_test_assert_error_message_{dialog_nonce}"),
        ("assert_actual", f"suite_add_test_assert_actual_{dialog_nonce}"),
        ("assert_expected", f"suite_add_test_assert_expected_{dialog_nonce}"),
        ("assert_expected_json_array_id", f"suite_add_test_assert_expected_json_array_id_{dialog_nonce}"),
        ("assert_compare_keys", f"suite_add_test_assert_compare_keys_{dialog_nonce}"),
    ]
    try:
        for source_suffix, legacy_key in field_mappings:
            original_keys.append((legacy_key, st.session_state.get(legacy_key)))
            value = st.session_state.get(_command_form_key(key_prefix, dialog_nonce, source_suffix))
            if value is None:
                st.session_state.pop(legacy_key, None)
            else:
                st.session_state[legacy_key] = value
        return _build_test_command_draft(dialog_nonce, command_ui_code)
    finally:
        for legacy_key, original_value in original_keys:
            if original_value is None and legacy_key in st.session_state:
                st.session_state.pop(legacy_key, None)
            elif original_value is not None:
                st.session_state[legacy_key] = original_value


def _render_suite_item_operation(
    item: dict,
    operation: dict,
    op_idx: int,
    owner_kind: str,
):
    item_ui_key = str(item.get("_ui_key") or new_ui_key())
    item["_ui_key"] = item_ui_key
    operation_ui_key = str(operation.get("_ui_key") or f"{item_ui_key}_op_{op_idx}")
    operation["_ui_key"] = operation_ui_key
    command_group = (
        _resolve_hook_command_group(operation.get("configuration_json"))
        if owner_kind == "hook"
        else _resolve_test_command_group(operation.get("configuration_json"))
    )
    row_cols = st.columns([18, 1], gap="small", vertical_alignment="top")
    with row_cols[0]:
        with st.container(border=True):
            st.markdown(_build_suite_command_markdown(operation))
    with row_cols[1]:
        if st.button(
            "",
            key=f"suite_editor_edit_command_{item_ui_key}_{operation_ui_key}",
            icon=":material/more_vert:",
            help="Modify command",
            type="tertiary",
            use_container_width=True,
        ):
            _open_edit_command_dialog(item_ui_key, operation_ui_key, owner_kind, command_group or "fallback-json")
            st.rerun()


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
            _render_suite_item_operation(hook, operation, op_idx, "hook")
    else:
        st.caption("Nessuna operation configurata.")

    add_cols = st.columns([1, 1, 1, 1], gap="small", vertical_alignment="center")
    with add_cols[1]:
        if st.button(
            "Add context command",
            key=f"suite_editor_add_context_command_{hook_phase}_{str((hook or {}).get('_ui_key') or hook_phase)}",
            icon=":material/add:",
            use_container_width=True,
        ):
            _open_hook_command_dialog_for_hook(draft, hook_phase, "context")
            st.rerun()
    with add_cols[2]:
        if st.button(
            "Add action",
            key=f"suite_editor_add_action_command_{hook_phase}_{str((hook or {}).get('_ui_key') or hook_phase)}",
            icon=":material/add:",
            use_container_width=True,
        ):
            _open_hook_command_dialog_for_hook(draft, hook_phase, "action")
            st.rerun()


def _ensure_test_item(test: dict, index: int) -> dict:
    test["_ui_key"] = str(test.get("_ui_key") or new_ui_key())
    if not isinstance(test.get("operations"), list):
        test["operations"] = []
    if not str(test.get("kind") or "").strip():
        test["kind"] = "test"
    return test


def _find_test_index_by_ui_key(draft: dict, test_ui_key: str) -> int:
    tests = draft.get("tests") or []
    if not isinstance(tests, list):
        return -1
    for index, test in enumerate(tests):
        if isinstance(test, dict) and str(test.get("_ui_key") or "") == str(test_ui_key or ""):
            return index
    return -1


def _find_test_by_ui_key(draft: dict, test_ui_key: str) -> dict | None:
    test_index = _find_test_index_by_ui_key(draft, test_ui_key)
    tests = draft.get("tests") or []
    if test_index < 0 or not isinstance(tests, list):
        return None
    test_item = tests[test_index]
    return test_item if isinstance(test_item, dict) else None


def _test_label(test: dict, index: int) -> str:
    description = str(test.get("description") or "").strip()
    test_id = str(test.get("id") or "").strip()
    return description or test_id or f"Test {index}"


def _render_test_item(test: dict, index: int, execution_state: dict):
    current_test = _ensure_test_item(test, index)
    row_cols = st.columns([20, 1], gap="small", vertical_alignment="top")
    with row_cols[0]:
        with st.expander(_test_label(current_test, index), expanded=True):
            operations = current_test.get("operations") or []
            if operations:
                for op_idx, operation in enumerate(operations):
                    _render_suite_item_operation(current_test, operation, op_idx, "test")
            else:
                st.caption("Nessun command configurato.")

            add_cols = st.columns([1,1, 1, 1,1], gap="small", vertical_alignment="center")
            with add_cols[1]:
                if st.button(
                    "Add constant",
                    key=f"suite_editor_add_test_constant_{current_test.get('_ui_key')}",
                    icon=":material/add:",
                    use_container_width=True,
                ):
                    _open_test_command_dialog_for_item(str(current_test.get("_ui_key") or ""), "constant")
                    st.rerun()
            with add_cols[2]:
                if st.button(
                    "Add action",
                    key=f"suite_editor_add_test_action_{current_test.get('_ui_key')}",
                    icon=":material/add:",
                    use_container_width=True,
                ):
                    _open_test_command_dialog_for_item(str(current_test.get("_ui_key") or ""), "action")
                    st.rerun()
            with add_cols[3]:
                if st.button(
                    "Add assert",
                    key=f"suite_editor_add_test_assert_{current_test.get('_ui_key')}",
                    icon=":material/add:",
                    use_container_width=True,
                ):
                    _open_test_command_dialog_for_item(str(current_test.get("_ui_key") or ""), "assert")
                    st.rerun()
    with row_cols[1]:
        if st.button(
            "",
            key=f"suite_editor_edit_test_{current_test.get('_ui_key')}",
            icon=":material/more_vert:",
            help="Modify test",
            type="tertiary",
            use_container_width=True,
        ):
            _open_edit_test_dialog(str(current_test.get("_ui_key") or ""))
            st.rerun()


@st.dialog("Add hook command", width="large")
def _render_add_hook_command_dialog(draft: dict):
    dialog_nonce = int(st.session_state.get(HOOK_ADD_COMMAND_DIALOG_NONCE_KEY, 0))
    hook_ui_key = str(st.session_state.get(HOOK_ADD_COMMAND_DIALOG_TARGET_UI_KEY) or "").strip()
    command_group = str(st.session_state.get(HOOK_ADD_COMMAND_DIALOG_GROUP_KEY) or "context").strip().lower()
    hook_item = find_draft_test_by_ui_key(draft, hook_ui_key)

    if not isinstance(hook_item, dict):
        st.error("Hook di destinazione non trovato.")
        if st.button("Cancel", key=f"suite_hook_add_command_missing_cancel_{dialog_nonce}", use_container_width=True):
            _close_hook_command_dialog()
            st.rerun()
        return

    load_test_editor_context(force=False)
    load_database_connections(force=False)

    json_arrays = _safe_list(st.session_state.get(TEST_EDITOR_JSON_ARRAYS_KEY, []))
    datasources = _safe_list(st.session_state.get(TEST_EDITOR_DATABASE_DATASOURCES_KEY, []))
    brokers = _safe_list(st.session_state.get(TEST_EDITOR_BROKERS_KEY, []))
    connections = _safe_list(st.session_state.get(DATABASE_CONNECTIONS_KEY, []))
    default_context = _default_context_for_item(hook_item)
    st.markdown("**Insert new one**")
    command_code = _render_hook_command_form(
        dialog_nonce,
        command_group,
        json_arrays,
        datasources,
        brokers,
        connections,
        draft,
        hook_item,
        stop_before_index=len(_operation_list(hook_item)),
        default_context=default_context,
        key_prefix="suite_hook_command",
    )

    action_cols = st.columns([1, 1], gap="small", vertical_alignment="center")
    with action_cols[0]:
        if st.button(
            "Add command",
            key=f"suite_add_hook_command_save_{dialog_nonce}",
            icon=":material/add_circle:",
            type="secondary",
            use_container_width=True,
        ):
            operation_item, validation_error = _build_hook_command_draft_with_prefix(
                dialog_nonce,
                command_code,
                key_prefix="suite_hook_command",
            )
            if validation_error:
                st.error(validation_error)
                return
            append_operation_to_test(hook_item, operation_item or {})
            _close_hook_command_dialog()
            st.session_state[SUITE_FEEDBACK_KEY] = "Nuovo command aggiunto."
            _persist_changes()
    with action_cols[1]:
        if st.button(
            "Cancel",
            key=f"suite_add_hook_command_cancel_{dialog_nonce}",
            use_container_width=True,
        ):
            _close_hook_command_dialog()
            st.rerun()


@st.dialog("Add test command", width="large")
def _render_add_test_command_dialog(draft: dict):
    dialog_nonce = int(st.session_state.get(TEST_ADD_COMMAND_DIALOG_NONCE_KEY, 0))
    test_ui_key = str(st.session_state.get(TEST_ADD_COMMAND_DIALOG_TARGET_UI_KEY) or "").strip()
    command_group = str(st.session_state.get(TEST_ADD_COMMAND_DIALOG_GROUP_KEY) or "constant").strip().lower()
    test_item = _find_test_by_ui_key(draft, test_ui_key)

    if not isinstance(test_item, dict):
        st.error("Test di destinazione non trovato.")
        if st.button("Cancel", key=f"suite_test_add_command_missing_cancel_{dialog_nonce}", use_container_width=True):
            _close_test_command_dialog()
            st.rerun()
        return

    load_test_editor_context(force=False)
    load_database_connections(force=False)

    json_arrays = _safe_list(st.session_state.get(TEST_EDITOR_JSON_ARRAYS_KEY, []))
    datasources = _safe_list(st.session_state.get(TEST_EDITOR_DATABASE_DATASOURCES_KEY, []))
    brokers = _safe_list(st.session_state.get(TEST_EDITOR_BROKERS_KEY, []))
    connections = _safe_list(st.session_state.get(DATABASE_CONNECTIONS_KEY, []))

    st.markdown("**Insert new one**")
    command_ui_code = _render_test_command_form(
        dialog_nonce,
        command_group,
        json_arrays,
        datasources,
        brokers,
        connections,
        draft,
        test_item,
        stop_before_index=len(_operation_list(test_item)),
        key_prefix="suite_test_command",
    )

    action_cols = st.columns([1, 1], gap="small", vertical_alignment="center")
    with action_cols[0]:
        if st.button(
            "Add command",
            key=f"suite_add_test_command_save_{dialog_nonce}",
            icon=":material/add_circle:",
            type="secondary",
            use_container_width=True,
        ):
            operation_item, validation_error = _build_test_command_draft_with_prefix(
                dialog_nonce,
                command_ui_code,
                key_prefix="suite_test_command",
            )
            if validation_error:
                st.error(validation_error)
                return
            append_operation_to_test(test_item, operation_item or {})
            _close_test_command_dialog()
            st.session_state[SUITE_FEEDBACK_KEY] = "Nuovo command aggiunto."
            _persist_changes()
    with action_cols[1]:
        if st.button(
            "Cancel",
            key=f"suite_add_test_command_cancel_{dialog_nonce}",
            use_container_width=True,
        ):
            _close_test_command_dialog()
            st.rerun()


def _render_generic_command_edit_dialog(item: dict, operation: dict, operation_index: int, dialog_nonce: int):
    description_key = _command_form_key("suite_generic_command_edit", dialog_nonce, "description")
    cfg_key = _command_form_key("suite_generic_command_edit", dialog_nonce, "cfg")
    if description_key not in st.session_state:
        st.session_state[description_key] = str(operation.get("description") or "")
    if cfg_key not in st.session_state:
        st.session_state[cfg_key] = json.dumps(_safe_dict(operation.get("configuration_json") or {}), ensure_ascii=True, indent=2)

    st.text_input("Description", key=description_key)
    st.text_area("Configuration JSON", key=cfg_key, height=240, help="Modifica i parametri del command come oggetto JSON.")

    action_cols = st.columns([1, 1, 1], gap="small", vertical_alignment="center")
    with action_cols[0]:
        if st.button("Save", key=f"suite_generic_command_edit_save_{dialog_nonce}", icon=":material/save:", type="secondary", use_container_width=True):
            description = str(st.session_state.get(description_key) or "").strip()
            if not description:
                st.error("Il campo Description e' obbligatorio.")
                return
            try:
                configuration_json = json.loads(str(st.session_state.get(cfg_key) or "").strip() or "{}")
            except json.JSONDecodeError as exc:
                st.error(f"Configuration JSON non valido: {str(exc)}")
                return
            if not isinstance(configuration_json, dict):
                st.error("Configuration JSON deve essere un oggetto JSON.")
                return
            _update_operation_in_item(
                item,
                operation_index,
                {
                    "description": description,
                    "operation_type": _normalize_command_code(configuration_json) or str(operation.get("operation_type") or ""),
                    "configuration_json": configuration_json,
                },
            )
            _close_edit_command_dialog()
            _persist_changes()
    with action_cols[1]:
        if st.button("Delete", key=f"suite_generic_command_edit_delete_{dialog_nonce}", icon=":material/delete:", type="secondary", use_container_width=True):
            operations = item.get("operations") or []
            if isinstance(operations, list) and 0 <= operation_index < len(operations):
                operations.pop(operation_index)
            _close_edit_command_dialog()
            st.session_state[SUITE_FEEDBACK_KEY] = "Command rimosso."
            _persist_changes()
    with action_cols[2]:
        if st.button("Cancel", key=f"suite_generic_command_edit_cancel_{dialog_nonce}", use_container_width=True):
            _close_edit_command_dialog()
            st.rerun()


@st.dialog("Modify command", width="large")
def _render_edit_command_dialog(draft: dict):
    dialog_nonce = int(st.session_state.get(COMMAND_EDIT_DIALOG_NONCE_KEY, 0))
    item_ui_key = str(st.session_state.get(COMMAND_EDIT_DIALOG_TARGET_ITEM_UI_KEY) or "").strip()
    command_ui_key = str(st.session_state.get(COMMAND_EDIT_DIALOG_TARGET_COMMAND_UI_KEY) or "").strip()
    owner_kind = str(st.session_state.get(COMMAND_EDIT_DIALOG_OWNER_KIND_KEY) or "").strip().lower()
    command_group = str(st.session_state.get(COMMAND_EDIT_DIALOG_GROUP_KEY) or "").strip().lower()
    item = find_draft_test_by_ui_key(draft, item_ui_key)

    if not isinstance(item, dict):
        st.error("Elemento di destinazione non trovato.")
        if st.button("Cancel", key=f"suite_edit_command_missing_cancel_{dialog_nonce}", use_container_width=True):
            _close_edit_command_dialog()
            st.rerun()
        return

    operation_index, operation = _find_operation_by_ui_key(item, command_ui_key)
    if not isinstance(operation, dict):
        st.error("Command non trovato.")
        if st.button("Cancel", key=f"suite_edit_command_missing_operation_cancel_{dialog_nonce}", use_container_width=True):
            _close_edit_command_dialog()
            st.rerun()
        return

    if owner_kind not in {"hook", "test"} or command_group == "fallback-json":
        _render_generic_command_edit_dialog(item, operation, operation_index, dialog_nonce)
        return

    load_test_editor_context(force=False)
    load_database_connections(force=False)
    json_arrays = _safe_list(st.session_state.get(TEST_EDITOR_JSON_ARRAYS_KEY, []))
    datasources = _safe_list(st.session_state.get(TEST_EDITOR_DATABASE_DATASOURCES_KEY, []))
    brokers = _safe_list(st.session_state.get(TEST_EDITOR_BROKERS_KEY, []))
    connections = _safe_list(st.session_state.get(DATABASE_CONNECTIONS_KEY, []))

    if owner_kind == "hook":
        default_context = _default_context_for_item(item)
        _initialize_hook_command_form(
            dialog_nonce,
            operation,
            brokers,
            default_context=default_context,
            key_prefix="suite_edit_hook_command",
        )
        command_code = _render_hook_command_form(
            dialog_nonce,
            command_group,
            json_arrays,
            datasources,
            brokers,
            connections,
            draft,
            item,
            stop_before_index=operation_index,
            default_context=default_context,
            key_prefix="suite_edit_hook_command",
        )
    else:
        _initialize_test_command_form(dialog_nonce, operation, brokers, key_prefix="suite_edit_test_command")
        command_code = _render_test_command_form(
            dialog_nonce,
            command_group,
            json_arrays,
            datasources,
            brokers,
            connections,
            draft,
            item,
            stop_before_index=operation_index,
            key_prefix="suite_edit_test_command",
        )

    action_cols = st.columns([1, 1, 1], gap="small", vertical_alignment="center")
    with action_cols[0]:
        if st.button("Save", key=f"suite_edit_command_save_{dialog_nonce}", icon=":material/save:", type="secondary", use_container_width=True):
            if owner_kind == "hook":
                updated_operation, validation_error = _build_hook_command_draft_with_prefix(
                    dialog_nonce,
                    command_code,
                    key_prefix="suite_edit_hook_command",
                )
            else:
                updated_operation, validation_error = _build_test_command_draft_with_prefix(
                    dialog_nonce,
                    command_code,
                    key_prefix="suite_edit_test_command",
                )
            if validation_error:
                st.error(validation_error)
                return
            _update_operation_in_item(item, operation_index, updated_operation or {})
            _close_edit_command_dialog()
            _persist_changes()
    with action_cols[1]:
        if st.button("Delete", key=f"suite_edit_command_delete_{dialog_nonce}", icon=":material/delete:", type="secondary", use_container_width=True):
            operations = item.get("operations") or []
            if isinstance(operations, list) and 0 <= operation_index < len(operations):
                operations.pop(operation_index)
            _close_edit_command_dialog()
            st.session_state[SUITE_FEEDBACK_KEY] = "Command rimosso."
            _persist_changes()
    with action_cols[2]:
        if st.button("Cancel", key=f"suite_edit_command_cancel_{dialog_nonce}", use_container_width=True):
            _close_edit_command_dialog()
            st.rerun()


@st.dialog("Modify test", width="medium")
def _render_edit_test_dialog(draft: dict):
    dialog_nonce = int(st.session_state.get(TEST_EDIT_DIALOG_NONCE_KEY, 0))
    test_ui_key = str(st.session_state.get(TEST_EDIT_DIALOG_TARGET_UI_KEY) or "").strip()
    test_item = _find_test_by_ui_key(draft, test_ui_key)

    if not isinstance(test_item, dict):
        st.error("Test non trovato.")
        if st.button("Cancel", key=f"suite_edit_test_missing_cancel_{dialog_nonce}", use_container_width=True):
            _close_edit_test_dialog()
            st.rerun()
        return

    description_key = f"suite_edit_test_description_{dialog_nonce}"
    st.text_input(
        "Description",
        key=description_key,
        value=str(test_item.get("description") or ""),
    )

    action_cols = st.columns([1, 1, 1], gap="small", vertical_alignment="center")
    with action_cols[0]:
        if st.button(
            "Save",
            key=f"suite_edit_test_save_{dialog_nonce}",
            icon=":material/save:",
            type="secondary",
            use_container_width=True,
        ):
            description = str(st.session_state.get(description_key) or "").strip()
            if not description:
                st.error("Il campo Description e' obbligatorio.")
                return
            test_item["description"] = description
            _close_edit_test_dialog()
            _persist_changes()
    with action_cols[1]:
        if st.button(
            "Delete",
            key=f"suite_edit_test_delete_{dialog_nonce}",
            icon=":material/delete:",
            type="secondary",
            use_container_width=True,
        ):
            test_index = _find_test_index_by_ui_key(draft, test_ui_key)
            tests = draft.get("tests") or []
            if isinstance(tests, list) and 0 <= test_index < len(tests):
                tests.pop(test_index)
            _close_edit_test_dialog()
            st.session_state[SUITE_FEEDBACK_KEY] = "Test rimosso."
            _persist_changes()
    with action_cols[2]:
        if st.button(
            "Cancel",
            key=f"suite_edit_test_cancel_{dialog_nonce}",
            use_container_width=True,
        ):
            _close_edit_test_dialog()
            st.rerun()


@st.dialog("Add operation", width="large")
def _render_add_operation_dialog(draft: dict):
    render_add_test_operation_dialog(
        draft,
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
                st.session_state[PENDING_TEST_SUITE_EXECUTION_SELECTION_KEY] = execution_id
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
        
        st.divider()
        
        add_cols = st.columns([8, 2], gap="small", vertical_alignment="center")
        with add_cols[1]:
            if st.button(
                "",
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

    if _consume_hook_command_dialog_request():
        _render_add_hook_command_dialog(draft)

    if _consume_test_command_dialog_request():
        _render_add_test_command_dialog(draft)

    if _consume_edit_command_dialog_request():
        _render_edit_command_dialog(draft)

    if _consume_edit_test_dialog_request():
        _render_edit_test_dialog(draft)

    if bool(st.session_state.get(ADD_TEST_DIALOG_OPEN_KEY, False)):
        _render_add_test_dialog(draft)
