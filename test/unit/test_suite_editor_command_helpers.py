import sys
import types
from pathlib import Path


if "streamlit" not in sys.modules:
    streamlit_stub = types.ModuleType("streamlit")
    streamlit_stub.session_state = {}
    streamlit_stub.dialog = lambda *args, **kwargs: (lambda fn: fn)
    sys.modules["streamlit"] = streamlit_stub

PROJECT_ROOT = Path(__file__).resolve().parents[2]
UI_ROOT = PROJECT_ROOT / "app" / "ui"
if str(UI_ROOT) not in sys.path:
    sys.path.insert(0, str(UI_ROOT))


from ui.test_suites.components import suite_editor_component


def _reset_session_state():
    sys.modules["streamlit"].session_state.clear()


def test_build_suite_command_summary_for_init_constant():
    _reset_session_state()
    command = {
        "description": "load rows",
        "configuration_json": {
            "commandCode": "initConstant",
            "commandType": "context",
            "name": "rows",
            "sourceType": "jsonArray",
        },
    }

    assert suite_editor_component._build_suite_command_markdown(command) == "**Initialize json array variable** *rows*"


def test_build_suite_command_summary_for_delete_constant():
    _reset_session_state()
    command = {
        "description": "cleanup",
        "configuration_json": {
            "commandCode": "deleteConstant",
            "commandType": "context",
            "name": "rows",
        },
    }

    assert suite_editor_component._build_suite_command_markdown(command) == "*rows*"


def test_build_suite_command_summary_omits_dash_when_description_is_empty():
    _reset_session_state()
    command = {
        "description": "",
        "configuration_json": {
            "commandCode": "initConstant",
            "commandType": "context",
            "name": "rows",
        },
    }

    assert suite_editor_component._build_suite_command_markdown(command) == "**Initialize generic variable** *rows*"


def test_build_suite_command_summary_for_table_commands():
    _reset_session_state()
    save_table_command = {
        "description": "persist rows",
        "configuration_json": {
            "commandCode": "saveTable",
            "commandType": "action",
            "table_name": "orders_tmp",
        },
    }
    drop_table_command = {
        "description": "",
        "configuration_json": {
            "commandCode": "dropTable",
            "commandType": "action",
            "table_name": "orders_tmp",
        },
    }
    clean_table_command = {
        "description": "truncate staging",
        "configuration_json": {
            "commandCode": "cleanTable",
            "commandType": "action",
            "table_name": "orders_tmp",
        },
    }

    assert suite_editor_component._build_suite_command_markdown(save_table_command) == "*orders_tmp*"
    assert suite_editor_component._build_suite_command_markdown(drop_table_command) == "*orders_tmp*"
    assert suite_editor_component._build_suite_command_markdown(clean_table_command) == "*orders_tmp*"


def test_build_suite_command_summary_for_send_message_queue(monkeypatch):
    _reset_session_state()
    sys.modules["streamlit"].session_state[suite_editor_component.TEST_EDITOR_BROKERS_KEY] = [
        {"id": "broker-1", "description": "Broker one"}
    ]
    monkeypatch.setattr(
        suite_editor_component,
        "load_test_editor_queues_for_broker",
        lambda broker_id, force=False: [{"id": "queue-1", "description": "Orders queue"}],
    )
    command = {
        "description": "publish rows",
        "configuration_json": {
            "commandCode": "sendMessageQueue",
            "commandType": "action",
            "source": "$.local.constants.rows",
            "queue_id": "queue-1",
        },
    }

    assert (
        suite_editor_component._build_suite_command_markdown(command)
        == "**send variable** *rows* **to queue** *Orders queue*"
    )


def test_build_suite_command_summary_for_dataset_commands_uses_cache_labels():
    _reset_session_state()
    sys.modules["streamlit"].session_state[suite_editor_component.DATABASE_CONNECTIONS_KEY] = [
        {"id": "conn-1", "description": "Orders DB"}
    ]
    sys.modules["streamlit"].session_state[suite_editor_component.TEST_EDITOR_DATABASE_DATASOURCES_KEY] = [
        {
            "id": "dataset-1",
            "description": "Orders dataset",
            "payload": {"connection_id": "conn-1"},
        }
    ]
    export_command = {
        "description": "share rows",
        "configuration_json": {
            "commandCode": "exportDataset",
            "commandType": "action",
            "connection_id": "conn-1",
            "dataset_id": "dataset-1",
            "table_name": "orders_stage",
        },
    }
    drop_command = {
        "description": "",
        "configuration_json": {
            "commandCode": "dropDataset",
            "commandType": "action",
            "dataset_id": "dataset-1",
        },
    }
    clean_command = {
        "description": "clean target",
        "configuration_json": {
            "commandCode": "cleanDataset",
            "commandType": "action",
            "dataset_id": "dataset-1",
        },
    }

    assert suite_editor_component._build_suite_command_markdown(export_command) == "*Orders DB* *Orders dataset*"
    assert suite_editor_component._build_suite_command_markdown(drop_command) == "*Orders DB* *Orders dataset*"
    assert suite_editor_component._build_suite_command_markdown(clean_command) == "*Orders DB* *Orders dataset*"


def test_build_suite_command_summary_for_sleep_and_run_suite():
    _reset_session_state()
    sys.modules["streamlit"].session_state[suite_editor_component.TEST_SUITES_KEY] = [
        {"id": "suite-1", "description": "Nightly suite"}
    ]
    sleep_command = {
        "description": "wait broker",
        "configuration_json": {
            "commandCode": "sleep",
            "commandType": "action",
            "duration": 15,
        },
    }
    run_suite_command = {
        "description": "run smoke",
        "configuration_json": {
            "commandCode": "runSuite",
            "commandType": "action",
            "suite_id": "suite-1",
        },
    }

    assert suite_editor_component._build_suite_command_markdown(sleep_command) == "15s"
    assert suite_editor_component._build_suite_command_markdown(run_suite_command) == "*Nightly suite*"


def test_build_suite_command_summary_for_assert_uses_variable_name():
    _reset_session_state()
    command = {
        "description": "compare payload",
        "configuration_json": {
            "commandCode": "jsonArrayEquals",
            "commandType": "assert",
            "actual": "$.local.constants.rows",
        },
    }

    assert (
        suite_editor_component._build_suite_command_markdown(command)
        == "jsonArrayEquals jsonArray equals *rows*"
    )


def test_command_labels_use_variable_wording():
    _reset_session_state()
    command = {"configuration_json": {"commandCode": "initConstant", "sourceType": "dataset"}}

    assert suite_editor_component._command_ui_label(command) == "Dataset variable"
    assert suite_editor_component._command_action_label(command) == "dataset variable"


def test_hook_command_type_labels_use_advanced_wording():
    assert suite_editor_component._hook_command_type_label("initConstant") == "Initialize variable"
    assert suite_editor_component._hook_command_type_label("deleteConstant") == "Variable cleanup"


def test_suite_editor_constant_group_uses_implicit_command_type():
    command_options = suite_editor_component.TEST_CONSTANT_COMMAND_CODES
    command_ui_code = command_options[0] if command_options else ""

    assert command_ui_code == "initConstant"


def test_format_source_variable_option_uses_name_and_type():
    assert (
        suite_editor_component._format_source_variable_option(
            {"name": "rows", "value_type": "dataset"}
        )
        == "rows : dataset variable"
    )


def test_dataset_summary_falls_back_to_raw_ids_when_cache_is_missing():
    _reset_session_state()
    command = {
        "description": "",
        "configuration_json": {
            "commandCode": "dropDataset",
            "commandType": "action",
            "dataset_id": "dataset-42",
        },
    }

    assert suite_editor_component._build_suite_command_markdown(command) == "- *dataset-42*"


def test_resolve_hook_command_group():
    assert suite_editor_component._resolve_hook_command_group(
        {"commandCode": "initConstant", "commandType": "context"}
    ) == "context"
    assert suite_editor_component._resolve_hook_command_group(
        {"commandCode": "saveTable", "commandType": "action"}
    ) == "action"


def test_resolve_test_command_group():
    assert suite_editor_component._resolve_test_command_group(
        {"commandCode": "initConstant", "commandType": "context"}
    ) == "constant"
    assert suite_editor_component._resolve_test_command_group(
        {"commandCode": "saveTable", "commandType": "action"}
    ) == "action"
    assert suite_editor_component._resolve_test_command_group(
        {"commandCode": "jsonEquals", "commandType": "assert"}
    ) == "assert"


def test_default_context_for_item_uses_global_for_before_all_and_after_all():
    assert suite_editor_component._default_context_for_item({"kind": "hook", "hook_phase": "before-all"}) == "global"
    assert suite_editor_component._default_context_for_item({"kind": "hook", "hook_phase": "after-all"}) == "global"


def test_default_context_for_item_uses_local_for_before_each_test_and_after_each():
    assert suite_editor_component._default_context_for_item({"kind": "hook", "hook_phase": "before-each"}) == "local"
    assert suite_editor_component._default_context_for_item({"kind": "hook", "hook_phase": "after-each"}) == "local"
    assert suite_editor_component._default_context_for_item({"kind": "test"}) == "local"


def test_resolve_available_source_constants_for_test_action_includes_visible_compatible_constants():
    test_item = {
        "kind": "test",
        "description": "test",
        "operations": [
            {
                "configuration_json": {
                    "commandCode": "initConstant",
                    "commandType": "context",
                    "name": "localRows",
                    "context": "local",
                    "sourceType": "json",
                }
            }
        ],
    }
    draft = {
        "hooks": {
            "before-all": {
                "kind": "hook",
                "hook_phase": "before-all",
                "operations": [
                    {
                        "configuration_json": {
                            "commandCode": "initConstant",
                            "commandType": "context",
                            "name": "globalRows",
                            "context": "global",
                            "sourceType": "jsonArray",
                        }
                    }
                ],
            }
        },
        "tests": [test_item],
    }

    options = suite_editor_component._resolve_available_source_constants(
        draft,
        test_item,
        command_code="saveTable",
        stop_before_index=1,
    )

    assert [item["path"] for item in options] == [
        "$.global.constants.globalRows",
        "$.local.constants.localRows",
    ]


def test_resolve_available_source_constants_for_before_all_excludes_global_constants():
    hook_item = {
        "kind": "hook",
        "hook_phase": "before-all",
        "operations": [
            {
                "configuration_json": {
                    "commandCode": "initConstant",
                    "commandType": "context",
                    "name": "globalRows",
                    "context": "global",
                    "sourceType": "jsonArray",
                }
            }
        ],
    }
    draft = {
        "hooks": {
            "before-all": hook_item,
        },
        "tests": [],
    }

    options = suite_editor_component._resolve_available_source_constants(
        draft,
        hook_item,
        command_code="saveTable",
        stop_before_index=1,
    )

    assert options == []


def test_resolve_available_source_constants_for_send_message_queue_includes_raw_constants():
    test_item = {
        "kind": "test",
        "description": "test",
        "operations": [
            {
                "configuration_json": {
                    "commandCode": "initConstant",
                    "commandType": "context",
                    "name": "messageBody",
                    "context": "local",
                    "sourceType": "raw",
                }
            }
        ],
    }
    draft = {
        "hooks": {},
        "tests": [test_item],
    }

    options = suite_editor_component._resolve_available_source_constants(
        draft,
        test_item,
        command_code="sendMessageQueue",
        stop_before_index=1,
    )

    assert [item["path"] for item in options] == [
        "$.local.constants.messageBody",
    ]


def test_resolve_available_source_constants_for_send_message_queue_includes_dataset_constants():
    test_item = {
        "kind": "test",
        "description": "test",
        "operations": [
            {
                "configuration_json": {
                    "commandCode": "initConstant",
                    "commandType": "context",
                    "name": "messageDataset",
                    "context": "local",
                    "sourceType": "dataset",
                }
            }
        ],
    }
    draft = {
        "hooks": {},
        "tests": [test_item],
    }

    options = suite_editor_component._resolve_available_source_constants(
        draft,
        test_item,
        command_code="sendMessageQueue",
        stop_before_index=1,
    )

    assert [item["path"] for item in options] == [
        "$.local.constants.messageDataset",
    ]


def test_resequence_operations_rewrites_order_progressively():
    operations = [
        {"order": 4, "_ui_key": "op-4", "description": "fourth"},
        {"order": 9, "_ui_key": "op-9", "description": "ninth"},
    ]

    result = suite_editor_component._resequence_operations(operations)

    assert [item["order"] for item in result] == [1, 2]
    assert [item["_ui_key"] for item in result] == ["op-4", "op-9"]


def test_friendly_suite_validation_message_for_visibility_errors():
    message = suite_editor_component._friendly_suite_validation_message(
        "Constant reference 'def-rows' is not visible for command 'saveTable'."
    )

    assert message == "This order uses a variable before it is declared or after it has been deleted."


def test_friendly_suite_validation_message_for_duplicate_definition_errors():
    message = suite_editor_component._friendly_suite_validation_message(
        "Constant 'rows' is already defined in scope 'local'."
    )

    assert message == "This order declares the same variable twice in the same scope."


def test_friendly_suite_validation_message_for_non_writable_scope_errors():
    message = suite_editor_component._friendly_suite_validation_message(
        "Scope 'global' is not writable in section 'test'."
    )

    assert message == "This order writes a variable in a scope that is not allowed here."


def test_build_hook_command_draft_allows_empty_description():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    streamlit_module.session_state["suite_add_hook_command_description_1"] = ""
    streamlit_module.session_state["suite_add_hook_init_constant_name_1"] = "rows"
    streamlit_module.session_state["suite_add_hook_init_constant_context_1"] = "local"
    streamlit_module.session_state["suite_add_hook_init_constant_source_type_1"] = "raw"
    streamlit_module.session_state["suite_add_hook_init_constant_value_1"] = ""

    operation, error = suite_editor_component._build_hook_command_draft(1, "initConstant")

    assert error is None
    assert operation is not None
    assert operation["description"] == ""


def test_build_test_command_draft_allows_empty_description():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    streamlit_module.session_state["suite_add_test_command_description_1"] = ""
    streamlit_module.session_state["suite_add_test_init_constant_name_1"] = "rows"
    streamlit_module.session_state["suite_add_test_init_constant_context_1"] = "local"
    streamlit_module.session_state["suite_add_test_init_constant_source_type_1"] = "raw"
    streamlit_module.session_state["suite_add_test_init_constant_value_1"] = ""

    operation, error = suite_editor_component._build_test_command_draft(1, "initConstant")

    assert error is None
    assert operation is not None
    assert operation["description"] == ""
