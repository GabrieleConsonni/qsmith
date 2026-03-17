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


def test_build_suite_command_markdown_for_action():
    command = {
        "description": "send message",
        "configuration_json": {
            "commandCode": "sendMessageQueue",
            "commandType": "action",
        },
    }

    assert suite_editor_component._build_suite_command_markdown(command) == "**[sendMessageQueue]** - send message"


def test_build_suite_command_markdown_for_init_constant():
    command = {
        "description": "load rows",
        "configuration_json": {
            "commandCode": "initConstant",
            "commandType": "context",
            "name": "rows",
            "sourceType": "jsonArray",
        },
    }

    assert suite_editor_component._build_suite_command_markdown(command) == "**[initConstant] rows : jsonArray** - load rows"


def test_build_suite_command_markdown_for_delete_constant_without_source_type():
    command = {
        "description": "cleanup",
        "configuration_json": {
            "commandCode": "deleteConstant",
            "commandType": "context",
            "name": "rows",
        },
    }

    assert suite_editor_component._build_suite_command_markdown(command) == "**[deleteConstant] rows** - cleanup"


def test_build_suite_command_markdown_uses_dash_for_missing_values():
    command = {
        "description": "",
        "configuration_json": {
            "commandCode": "",
            "commandType": "assert",
        },
    }

    assert suite_editor_component._build_suite_command_markdown(command) == "**[-]** - -"


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
