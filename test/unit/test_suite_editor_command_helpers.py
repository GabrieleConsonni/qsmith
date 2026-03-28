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


from ui.test_suites.components import suite_editor_component, test_editor_component
from ui.elaborations_shared.components import test_command_component


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

    assert suite_editor_component._build_suite_command_markdown(command) == "**Delete variable** *rows*"


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
            "source": "$.local.constants.rows",
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

    assert suite_editor_component._build_suite_command_markdown(save_table_command) == "**Save variable** *rows* **to table** *orders_tmp*"
    assert suite_editor_component._build_suite_command_markdown(drop_table_command) == "**Drop table** *orders_tmp*"
    assert suite_editor_component._build_suite_command_markdown(clean_table_command) == "**Clean table** *orders_tmp*"


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
        == "**Send variable** *rows* **to queue** *Orders queue*"
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
            "source": "$.local.constants.rows",
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

    assert suite_editor_component._build_suite_command_markdown(export_command) == "**Export variable** *rows* **to table** *orders_stage*"
    assert suite_editor_component._build_suite_command_markdown(drop_command) == "**Drop dataset** *Orders dataset* **from** *Orders DB* **database**"
    assert suite_editor_component._build_suite_command_markdown(clean_command) == "**Clean dataset** *Orders dataset* **from** *Orders DB* **database**"


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

    assert suite_editor_component._build_suite_command_markdown(sleep_command) == "**Sleep** *15s*"
    assert suite_editor_component._build_suite_command_markdown(run_suite_command) == "**Run suite** *Nightly suite*"


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
        == "**Expected JsonArray equals to** *rows*"
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
        == "rows:dataset"
    )


def test_queue_variable_uses_move_to_inbox_icon():
    command = {"configuration_json": {"commandCode": "initConstant", "sourceType": "sqsQueue"}}

    assert suite_editor_component._command_leading_icon(command) == ":material/move_to_inbox:"


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

    assert suite_editor_component._build_suite_command_markdown(command) == "**Drop dataset** *dataset-42* **from** - **database**"


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


def test_resolve_available_source_constants_for_send_message_queue_keeps_raw_preview_value():
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
                    "value": '{"hello": "world"}',
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

    assert options[0]["preview_value"] == '{"hello": "world"}'


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


def test_build_test_command_draft_for_send_message_queue_includes_message_template():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    streamlit_module.session_state["suite_add_test_command_description_13"] = ""
    streamlit_module.session_state["suite_add_test_send_message_broker_id_13"] = "broker-1"
    streamlit_module.session_state["suite_add_test_send_message_queue_id_13"] = "queue-1"
    streamlit_module.session_state["suite_add_test_send_message_source_13"] = "$.local.constants.payload"
    streamlit_module.session_state["suite_add_test_send_message_template_enabled_13"] = True
    streamlit_module.session_state["suite_add_test_send_message_template_for_each_13"] = "$.body"
    streamlit_module.session_state["suite_add_test_send_message_template_fields_13"] = ["payload"]
    streamlit_module.session_state["suite_add_test_send_message_template_constants_rows_13"] = [
        {"field": "channel", "type": "string", "value": "sms"},
        {"field": "enabled", "type": "boolean", "value": "true"},
    ]

    operation, error = suite_editor_component._build_test_command_draft(13, "sendMessageQueue")

    assert error is None
    assert operation is not None
    assert operation["configuration_json"]["message_template"] == {
        "forEach": "$.body",
        "fields": ["payload"],
        "constants": [
            {"name": "channel", "kind": "string", "value": "sms"},
            {"name": "enabled", "kind": "boolean", "value": "true"},
        ],
    }


def test_resolve_send_message_preview_payload_uses_template_configuration():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    streamlit_module.session_state["suite_add_test_send_message_template_enabled_13"] = True
    streamlit_module.session_state["suite_add_test_send_message_template_for_each_13"] = "$.body"
    streamlit_module.session_state["suite_add_test_send_message_template_fields_13"] = ["payload"]
    streamlit_module.session_state["suite_add_test_send_message_template_constants_rows_13"] = [
        {"field": "channel", "type": "string", "value": "sms"},
    ]
    original_preview_api = suite_editor_component.preview_send_message_template_rows_via_api
    suite_editor_component.preview_send_message_template_rows_via_api = lambda **kwargs: [
        {"payload": {"id": 1, "status": "queued"}}
    ]

    try:
        preview_payload, preview_error = suite_editor_component._resolve_send_message_preview_payload(
            key_prefix="suite_add_test",
            dialog_nonce=13,
            source_definition={
                "path": "$.local.constants.payload",
                "value_type": "json",
                "preview_value": {"body": {"payload": {"id": 1, "status": "queued"}}},
            },
            json_arrays=[],
            datasources=[],
        )
    finally:
        suite_editor_component.preview_send_message_template_rows_via_api = original_preview_api

    assert preview_error is None
    assert preview_payload == {
        "payload": {"id": 1, "status": "queued"},
        "channel": "sms",
    }


def test_resolve_send_message_preview_payload_uses_raw_source_when_template_is_disabled():
    _reset_session_state()

    preview_payload, preview_error = suite_editor_component._resolve_send_message_preview_payload(
        key_prefix="suite_add_test",
        dialog_nonce=13,
        source_definition={
            "path": "$.local.constants.messageBody",
            "value_type": "raw",
            "preview_value": '{"hello": "world"}',
        },
        json_arrays=[],
        datasources=[],
    )

    assert preview_error is None
    assert preview_payload == '{"hello": "world"}'


def test_render_send_message_template_section_uses_distinct_data_editor_widget_key():
    _reset_session_state()
    session_state = sys.modules["streamlit"].session_state
    session_state["suite_add_test_send_message_template_enabled_13"] = True
    session_state["suite_add_test_send_message_source_13"] = "$.local.constants.payload"
    session_state["suite_add_test_send_message_template_constants_rows_13"] = [
        {"field": "channel", "type": "string", "value": "sms"}
    ]

    class _ColumnConfig:
        @staticmethod
        def TextColumn(*args, **kwargs):
            return {"args": args, "kwargs": kwargs}

        @staticmethod
        def SelectboxColumn(*args, **kwargs):
            return {"args": args, "kwargs": kwargs}

    class _Ctx:
        def __enter__(self):
            return None

        def __exit__(self, exc_type, exc, tb):
            return False

    class StreamlitStub:
        def __init__(self):
            self.session_state = session_state
            self.column_config = _ColumnConfig()
            self.data_editor_calls = []

        def checkbox(self, *args, **kwargs):
            return None

        def info(self, *args, **kwargs):
            return None

        def caption(self, *args, **kwargs):
            return None

        def json(self, *args, **kwargs):
            return None

        def text_input(self, *args, **kwargs):
            return None

        def multiselect(self, *args, **kwargs):
            return None

        def columns(self, spec, **kwargs):
            return [_Ctx() for _ in spec]

        def button(self, *args, **kwargs):
            return False

        def rerun(self):
            raise AssertionError("rerun should not be called")

        def data_editor(self, data, **kwargs):
            self.data_editor_calls.append({"data": data, **kwargs})
            return [{"field": "enabled", "type": "boolean", "value": "true"}]

    stub = StreamlitStub()
    original_st = suite_editor_component.st
    original_preview_helper = suite_editor_component._resolve_send_message_template_preview_rows
    try:
        suite_editor_component.st = stub
        suite_editor_component._resolve_send_message_template_preview_rows = (
            lambda *args, **kwargs: ([{"payload": {"id": 1}}], ["payload"], None)
        )
        suite_editor_component._render_send_message_template_section(
            key_prefix="suite_add_test",
            dialog_nonce=13,
            source_options=[{"path": "$.local.constants.payload", "value_type": "json"}],
            json_arrays=[],
            datasources=[],
        )
    finally:
        suite_editor_component.st = original_st
        suite_editor_component._resolve_send_message_template_preview_rows = original_preview_helper

    assert len(stub.data_editor_calls) == 1
    assert stub.data_editor_calls[0]["data"] == [
        {"field": "channel", "type": "string", "value": "sms"}
    ]
    assert stub.data_editor_calls[0]["key"] == "suite_add_test_send_message_template_constants_editor_13"
    assert stub.data_editor_calls[0]["key"] != "suite_add_test_send_message_template_constants_rows_13"
    assert session_state["suite_add_test_send_message_template_constants_rows_13"] == [
        {"field": "enabled", "type": "boolean", "value": "true"}
    ]


def test_test_action_command_options_do_not_repeat_export_dataset_label():
    labels = [
        suite_editor_component._command_ui_label(
            {
                "configuration_json": {
                    "commandCode": suite_editor_component.TEST_ACTION_COMMAND_MAPPING.get(code, code)
                }
            }
        )
        for code, _label in suite_editor_component.TEST_ACTION_COMMAND_OPTIONS
    ]

    assert labels.count("Export dataset") == 1


def test_append_operation_to_test_allows_empty_description():
    suite_test = {"operations": []}
    operation_item = {
        "description": "",
        "operation_type": "initconstant",
        "configuration_json": {
            "commandCode": "initConstant",
            "commandType": "context",
            "name": "rows",
        },
    }

    test_command_component.append_operation_to_test(suite_test, operation_item)

    assert len(suite_test["operations"]) == 1
    assert suite_test["operations"][0]["description"] == ""
    assert suite_test["operations"][0]["configuration_json"]["name"] == "rows"


def test_command_group_copy_uses_type_specific_labels():
    assert suite_editor_component._command_group_label("context") == "variable"
    assert suite_editor_component._command_group_label("constant") == "variable"
    assert suite_editor_component._command_group_label("action") == "action"
    assert suite_editor_component._command_group_label("assert") == "assert"
    assert suite_editor_component._command_group_intro_label("constant", mode="add") == "Insert new variable"
    assert suite_editor_component._command_group_intro_label("action", mode="edit") == "Modify action"
    assert suite_editor_component._command_group_primary_action_label("context", mode="edit") == "Save variable"
    assert suite_editor_component._command_group_primary_action_label("assert", mode="add") == "Add assert"
    assert suite_editor_component._command_group_added_feedback("context") == "New variable added."
    assert suite_editor_component._command_group_updated_feedback("action") == "Action updated."


def test_build_test_command_draft_for_json_equals_with_manual_expected():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    streamlit_module.session_state["suite_add_test_command_description_7"] = ""
    streamlit_module.session_state["suite_add_test_assert_actual_7"] = "$.local.constants.actualPayload"
    streamlit_module.session_state["suite_add_test_assert_expected_mode_7"] = "manual"
    streamlit_module.session_state["suite_add_test_assert_expected_7"] = '{"ok": true}'

    operation, error = suite_editor_component._build_test_command_draft(7, "jsonEquals")

    assert error is None
    assert operation["configuration_json"]["actual"] == "$.local.constants.actualPayload"
    assert operation["configuration_json"]["expected"] == {"ok": True}


def test_build_test_command_draft_for_json_equals_with_expected_variable():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    streamlit_module.session_state["suite_add_test_command_description_8"] = ""
    streamlit_module.session_state["suite_add_test_assert_actual_8"] = "$.local.constants.actualPayload"
    streamlit_module.session_state["suite_add_test_assert_expected_mode_8"] = "variable"
    streamlit_module.session_state["suite_add_test_assert_expected_variable_8"] = "$.global.constants.expectedPayload"

    operation, error = suite_editor_component._build_test_command_draft(8, "jsonEquals")

    assert error is None
    assert operation["configuration_json"]["expected"] == {
        "$ref": "$.global.constants.expectedPayload"
    }


def test_build_test_command_draft_for_json_contains_uses_manual_expected_and_compare_keys():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    streamlit_module.session_state["suite_add_test_command_description_9"] = ""
    streamlit_module.session_state["suite_add_test_assert_actual_9"] = "$.local.constants.actualPayload"
    streamlit_module.session_state["suite_add_test_assert_expected_mode_9"] = "manual"
    streamlit_module.session_state["suite_add_test_assert_expected_9"] = '{"id": 1, "code": "A"}'
    streamlit_module.session_state["suite_add_test_assert_compare_keys_9"] = ["id", "code"]

    operation, error = suite_editor_component._build_test_command_draft(9, "jsonContains")

    assert error is None
    assert operation["configuration_json"]["expected"] == {"id": 1, "code": "A"}
    assert operation["configuration_json"]["compare_keys"] == ["id", "code"]


def test_build_test_command_draft_for_json_array_asserts_use_multiselect_compare_keys():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    streamlit_module.session_state["suite_add_test_command_description_10"] = ""
    streamlit_module.session_state["suite_add_test_assert_actual_10"] = "$.local.constants.actualRows"
    streamlit_module.session_state["suite_add_test_assert_expected_json_array_id_10"] = "ja-1"
    streamlit_module.session_state["suite_add_test_assert_compare_keys_10"] = ["id", "code"]

    equals_operation, equals_error = suite_editor_component._build_test_command_draft(10, "jsonArrayEquals")
    contains_operation, contains_error = suite_editor_component._build_test_command_draft(10, "jsonArrayContains")

    assert equals_error is None
    assert equals_operation["configuration_json"]["expected_json_array_id"] == "ja-1"
    assert equals_operation["configuration_json"]["compare_keys"] == ["id", "code"]
    assert contains_error is None
    assert contains_operation["configuration_json"]["compare_keys"] == ["id", "code"]


def test_build_test_command_draft_for_json_empty_requires_actual_variable():
    _reset_session_state()
    sys.modules["streamlit"].session_state["suite_add_test_command_description_11"] = ""

    operation, error = suite_editor_component._build_test_command_draft(11, "jsonEmpty")

    assert operation is None
    assert error == "Il campo Actual variable e' obbligatorio."


def test_build_test_command_draft_for_dataset_init_constant_includes_parameter_bindings():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    streamlit_module.session_state[suite_editor_component.TEST_EDITOR_DATABASE_DATASOURCES_KEY] = [
        {
            "id": "dataset-1",
            "description": "Orders dataset",
            "perimeter": {
                "parameters": [
                    {
                        "name": "pipelineId",
                        "type": "string",
                        "required": True,
                    }
                ]
            },
        }
    ]
    streamlit_module.session_state["suite_add_test_command_description_12"] = ""
    streamlit_module.session_state["suite_add_test_init_constant_name_12"] = "rows"
    streamlit_module.session_state["suite_add_test_init_constant_context_12"] = "local"
    streamlit_module.session_state["suite_add_test_init_constant_source_type_12"] = "dataset"
    streamlit_module.session_state["suite_add_test_init_constant_dataset_id_12"] = "dataset-1"
    streamlit_module.session_state["suite_test_command_init_constant_dataset_param_mode_pipelineId_12"] = "constant"
    streamlit_module.session_state["suite_test_command_init_constant_dataset_param_source_pipelineId_12"] = "$.global.constants.pipelineId"

    operation, error = suite_editor_component._build_test_command_draft(12, "initConstant")

    assert error is None
    assert operation is not None
    assert operation["configuration_json"]["parameters"] == {
        "pipelineId": {
            "kind": "constant_path",
            "path": "$.global.constants.pipelineId",
        }
    }


def test_resolve_available_assert_expected_constants_for_json_contains_only_returns_inspectable_json():
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
                            "name": "inspectableExpected",
                            "context": "global",
                            "sourceType": "json",
                            "value": {"id": 1, "code": "A"},
                        }
                    },
                    {
                        "configuration_json": {
                            "commandCode": "initConstant",
                            "commandType": "context",
                            "name": "nonInspectableExpected",
                            "context": "global",
                            "sourceType": "json",
                            "value": [1, 2, 3],
                        }
                    },
                ],
            }
        },
        "tests": [
            {
                "kind": "test",
                "description": "test",
                "operations": [],
            }
        ],
    }

    options = suite_editor_component._resolve_available_assert_constants(
        draft,
        draft["tests"][0],
        command_code="jsonContains",
        role="expected",
    )

    assert [item["path"] for item in options] == ["$.global.constants.inspectableExpected"]


def test_initialize_test_command_form_hydrates_json_contains_expected_ref_and_legacy_array():
    _reset_session_state()
    ref_operation = {
        "description": "",
        "configuration_json": {
            "commandCode": "jsonContains",
            "commandType": "assert",
            "actual": "$.local.constants.actualPayload",
            "expected": {"$ref": "$.global.constants.expectedPayload"},
            "compare_keys": ["id"],
        },
    }

    suite_editor_component._initialize_test_command_form(
        12,
        ref_operation,
        [],
        [],
        key_prefix="suite_edit_test_command",
    )

    session_state = sys.modules["streamlit"].session_state
    assert session_state["suite_edit_test_command_assert_expected_mode_12"] == "variable"
    assert (
        session_state["suite_edit_test_command_assert_expected_variable_12"]
        == "$.global.constants.expectedPayload"
    )

    _reset_session_state()
    legacy_operation = {
        "description": "",
        "configuration_json": {
            "commandCode": "jsonContains",
            "commandType": "assert",
            "actual": "$.local.constants.actualPayload",
            "expected_json_array_id": "ja-legacy",
            "compare_keys": ["id"],
        },
    }

    suite_editor_component._initialize_test_command_form(
        13,
        legacy_operation,
        [{"id": "ja-legacy", "payload": [{"id": 1, "code": "A"}]}],
        [],
        key_prefix="suite_edit_test_command",
    )

    session_state = sys.modules["streamlit"].session_state
    assert session_state["suite_edit_test_command_assert_expected_mode_13"] == "manual"
    assert '"id": 1' in session_state["suite_edit_test_command_assert_expected_13"]
    assert session_state["suite_edit_test_command_assert_compare_keys_13"] == ["id"]


def test_build_assert_summary_uses_requested_restyle_for_empty_and_contains():
    _reset_session_state()
    contains_command = {
        "configuration_json": {
            "commandCode": "jsonContains",
            "commandType": "assert",
            "actual": "$.local.constants.payload",
        }
    }
    empty_command = {
        "configuration_json": {
            "commandCode": "jsonArrayNotEmpty",
            "commandType": "assert",
            "actual": "$.local.constants.rows",
        }
    }

    assert suite_editor_component._build_suite_command_markdown(contains_command) == "**Expected Json contains** *payload*"
    assert suite_editor_component._build_suite_command_markdown(empty_command) == "**JsonArray** *rows* **is not empty**"


def test_resolve_export_dataset_mapping_key_options_for_json_json_array_and_dataset():
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
                            "name": "payload",
                            "context": "global",
                            "sourceType": "json",
                            "value": {"id": 1, "code": "A"},
                        }
                    },
                    {
                        "configuration_json": {
                            "commandCode": "initConstant",
                            "commandType": "context",
                            "name": "rows",
                            "context": "global",
                            "sourceType": "jsonArray",
                            "json_array_id": "ja-1",
                        }
                    },
                    {
                        "configuration_json": {
                            "commandCode": "initConstant",
                            "commandType": "context",
                            "name": "datasetRows",
                            "context": "global",
                            "sourceType": "dataset",
                            "dataset_id": "ds-1",
                        }
                    },
                ],
            }
        },
        "tests": [{"kind": "test", "description": "test", "operations": []}],
    }
    item = draft["tests"][0]
    json_arrays = [{"id": "ja-1", "payload": [{"id": 1, "status": "OK"}]}]
    datasources = [
        {
            "id": "ds-1",
            "payload": {"connection_id": "conn-1"},
            "perimeter": {"selected_columns": ["id", "status"]},
        }
    ]

    json_keys, json_error = suite_editor_component._resolve_export_dataset_mapping_key_options(
        draft,
        item,
        source_path="$.global.constants.payload",
        stop_before_index=None,
        json_arrays=json_arrays,
        datasources=datasources,
    )
    json_array_keys, json_array_error = suite_editor_component._resolve_export_dataset_mapping_key_options(
        draft,
        item,
        source_path="$.global.constants.rows",
        stop_before_index=None,
        json_arrays=json_arrays,
        datasources=datasources,
    )
    dataset_keys, dataset_error = suite_editor_component._resolve_export_dataset_mapping_key_options(
        draft,
        item,
        source_path="$.global.constants.datasetRows",
        stop_before_index=None,
        json_arrays=json_arrays,
        datasources=datasources,
    )

    assert json_error is None
    assert json_keys == ["id", "code"]
    assert json_array_error is None
    assert json_array_keys == ["id", "status"]
    assert dataset_error is None
    assert dataset_keys == ["id", "status"]


def test_test_item_summary_view_only_exposes_modify_button():
    _reset_session_state()
    current_test = {
        "_ui_key": "test-ui-1",
        "description": "Unsaved test",
        "operations": [],
    }

    class StreamlitStub:
        def __init__(self):
            self.session_state = sys.modules["streamlit"].session_state
            self.button_calls = []

        def expander(self, *args, **kwargs):
            class _Ctx:
                def __enter__(self_inner):
                    return None

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

            return _Ctx()

        def columns(self, spec, **kwargs):
            class _Col:
                def __enter__(self_inner):
                    return None

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

            return [_Col() for _ in spec]

        def caption(self, *args, **kwargs):
            return None

        def markdown(self, *args, **kwargs):
            return None

        def divider(self, *args, **kwargs):
            return None

        def button(self, *args, **kwargs):
            payload = dict(kwargs)
            if args:
                payload["label"] = args[0]
            self.button_calls.append(payload)
            return False

        def rerun(self):
            raise AssertionError("rerun should not be called")

    stub = StreamlitStub()
    original_st = suite_editor_component.st
    try:
        suite_editor_component.st = stub
        suite_editor_component._render_test_item(current_test, 1, {})
    finally:
        suite_editor_component.st = original_st

    modify_button_call = next(
        call for call in stub.button_calls if call.get("key") == "test_suite_open_test_editor_test-ui-1"
    )
    assert modify_button_call["label"] == ""
    delete_button_call = next(
        call for call in stub.button_calls if call.get("key") == "test_suite_delete_test_test-ui-1"
    )
    assert delete_button_call["label"] == ""
    assert len(stub.button_calls) == 2


def test_ensure_selected_test_position_clamps_to_last_available():
    _reset_session_state()
    sys.modules["streamlit"].session_state[suite_editor_component.SELECTED_TEST_POSITION_KEY] = 5
    draft = {
        "tests": [
            {"description": "First", "position": 1},
            {"description": "Second", "position": 2},
        ]
    }

    assert suite_editor_component._ensure_selected_test_position(draft) == 2
    assert sys.modules["streamlit"].session_state[suite_editor_component.SELECTED_TEST_POSITION_KEY] == 2


def test_render_add_test_dialog_appends_test_and_selects_it():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    streamlit_module.session_state[suite_editor_component.ADD_TEST_DIALOG_NONCE_KEY] = 7
    streamlit_module.session_state["suite_add_test_description_7"] = "Smoke test"
    streamlit_module.session_state["suite_add_test_on_failure_7"] = "CONTINUE"
    draft = {"id": "suite-1", "tests": []}
    persist_calls = []
    close_calls = []

    class StreamlitStub:
        def __init__(self):
            self.session_state = streamlit_module.session_state

        def text_input(self, *args, **kwargs):
            return None

        def selectbox(self, *args, **kwargs):
            return None

        def columns(self, spec, **kwargs):
            class _Col:
                def __enter__(self_inner):
                    return None

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

            return [_Col() for _ in spec]

        def button(self, label="", **kwargs):
            return label == "Save"

        def rerun(self):
            self.session_state["_rerun_called"] = True

    stub = StreamlitStub()
    original_st = suite_editor_component.st
    original_persist = suite_editor_component._persist_current_draft
    original_close = suite_editor_component._close_add_test_dialog
    try:
        suite_editor_component.st = stub
        suite_editor_component._persist_current_draft = lambda **kwargs: persist_calls.append(kwargs)
        suite_editor_component._close_add_test_dialog = lambda: close_calls.append(True)
        suite_editor_component._render_add_test_dialog(draft)
    finally:
        suite_editor_component.st = original_st
        suite_editor_component._persist_current_draft = original_persist
        suite_editor_component._close_add_test_dialog = original_close

    assert len(draft["tests"]) == 1
    assert draft["tests"][0]["kind"] == "test"
    assert draft["tests"][0]["description"] == "Smoke test"
    assert draft["tests"][0]["on_failure"] == "CONTINUE"
    assert draft["tests"][0]["position"] == 1
    assert streamlit_module.session_state[suite_editor_component.SELECTED_TEST_POSITION_KEY] == 1
    assert persist_calls == [{"success_message": "Test added.", "rerun": False}]
    assert close_calls == [True]
    assert streamlit_module.session_state["_rerun_called"] is True


def test_move_operation_in_item_swaps_and_resequences():
    item = {
        "operations": [
            {"_ui_key": "op-1", "order": 1, "description": "first"},
            {"_ui_key": "op-2", "order": 2, "description": "second"},
        ]
    }

    assert suite_editor_component._move_operation_in_item(item, 0, 1) is True
    assert [operation["_ui_key"] for operation in item["operations"]] == ["op-2", "op-1"]
    assert [operation["order"] for operation in item["operations"]] == [1, 2]


def test_test_editor_item_read_mode_exposes_inline_command_actions():
    _reset_session_state()
    current_test = {
        "_ui_key": "test-ui-1",
        "description": "Editable test",
        "operations": [
            {
                "_ui_key": "op-ui-1",
                "description": "cleanup",
                "configuration_json": {
                    "commandCode": "dropTable",
                    "commandType": "action",
                    "table_name": "orders_tmp",
                },
            }
        ],
    }
    draft = {"tests": [current_test]}

    class StreamlitStub:
        def __init__(self):
            self.session_state = sys.modules["streamlit"].session_state
            self.button_calls = []

        def container(self, *args, **kwargs):
            class _Ctx:
                def __enter__(self_inner):
                    return None

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

            return _Ctx()

        def columns(self, spec, **kwargs):
            class _Col:
                def __enter__(self_inner):
                    return None

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

            return [_Col() for _ in spec]

        def caption(self, *args, **kwargs):
            return None

        def markdown(self, *args, **kwargs):
            return None

        def divider(self, *args, **kwargs):
            return None

        def button(self, *args, **kwargs):
            payload = dict(kwargs)
            if args:
                payload["label"] = args[0]
            self.button_calls.append(payload)
            return False

        def rerun(self):
            raise AssertionError("rerun should not be called")

    stub = StreamlitStub()
    original_st = test_editor_component.st
    try:
        test_editor_component.st = stub
        test_editor_component._render_test_editor_item(current_test, 1, draft, {})
    finally:
        test_editor_component.st = original_st

    keys = {call.get("key") for call in stub.button_calls}
    assert "test_editor_inline_command_modify_test-ui-1_op-ui-1" in keys
    assert "test_editor_inline_command_delete_test-ui-1_op-ui-1" in keys
    assert "test_editor_inline_command_up_test-ui-1_op-ui-1" in keys
    assert "test_editor_inline_command_down_test-ui-1_op-ui-1" in keys
