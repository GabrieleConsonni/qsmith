import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
UI_ROOT = PROJECT_ROOT / "app" / "ui"
if str(UI_ROOT) not in sys.path:
    sys.path.insert(0, str(UI_ROOT))


from test_suites.services.draft_mapper import build_test_suite_draft, draft_to_test_suite_payload


def test_build_test_suite_draft_hydrates_ref_based_commands_for_ui_editing():
    payload = {
        "id": "suite-1",
        "description": "suite",
        "hooks": [
            {
                "hook_phase": "before-all",
                "description": "before all",
                "commands": [
                    {
                        "order": 1,
                        "description": "load rows",
                        "cfg": {
                            "commandCode": "initConstant",
                            "commandType": "context",
                            "definitionId": "def-rows",
                            "name": "rows",
                            "context": "global",
                            "sourceType": "jsonArray",
                            "json_array_id": "json-array-1",
                        },
                    }
                ],
            }
        ],
        "tests": [
            {
                "description": "test 1",
                "commands": [
                    {
                        "order": 1,
                        "description": "send message",
                        "cfg": {
                            "commandCode": "sendMessageQueue",
                            "commandType": "action",
                            "queue_id": "queue-1",
                            "sourceConstantRef": {"definitionId": "def-rows"},
                            "resultConstant": {
                                "definitionId": "def-publish-result",
                                "name": "publishResult",
                                "valueType": "json",
                            },
                        },
                    },
                    {
                        "order": 2,
                        "description": "assert publish result",
                        "cfg": {
                            "commandCode": "jsonEquals",
                            "commandType": "assert",
                            "actualConstantRef": {"definitionId": "def-publish-result"},
                            "expected": {"ok": True},
                        },
                    },
                ],
            }
        ],
    }

    draft = build_test_suite_draft(payload)

    before_all_cfg = draft["hooks"]["before-all"]["operations"][0]["configuration_json"]
    send_cfg = draft["tests"][0]["operations"][0]["configuration_json"]
    assert_cfg = draft["tests"][0]["operations"][1]["configuration_json"]

    assert before_all_cfg["definitionId"] == "def-rows"
    assert send_cfg["source"] == "$.global.constants.rows"
    assert send_cfg["result_target"] == "$.result.constants.publishResult"
    assert assert_cfg["actual"] == "$.result.constants.publishResult"


def test_draft_to_test_suite_payload_converts_legacy_suite_editor_fields_to_qsm_039_contract():
    draft = {
        "id": "suite-1",
        "description": "suite",
        "hooks": {
            "before-all": {
                "kind": "hook",
                "hook_phase": "before-all",
                "description": "before all",
                "operations": [
                    {
                        "order": 1,
                        "description": "load rows",
                        "configuration_json": {
                            "commandCode": "initConstant",
                            "commandType": "context",
                            "name": "rows",
                            "context": "global",
                            "sourceType": "jsonArray",
                            "json_array_id": "json-array-1",
                        },
                    }
                ],
            }
        },
        "tests": [
            {
                "kind": "test",
                "description": "test 1",
                "operations": [
                    {
                        "order": 1,
                        "description": "send message",
                        "configuration_json": {
                            "commandCode": "sendMessageQueue",
                            "commandType": "action",
                            "queue_id": "queue-1",
                            "source": "$.global.constants.rows",
                            "result_target": "$.result.constants.publishResult",
                        },
                    },
                    {
                        "order": 2,
                        "description": "assert publish result",
                        "configuration_json": {
                            "commandCode": "jsonEquals",
                            "commandType": "assert",
                            "actual": "$.result.constants.publishResult",
                            "expected": {"ok": True},
                        },
                    },
                ],
            }
        ],
    }

    payload = draft_to_test_suite_payload(draft)

    init_cfg = payload["hooks"][0]["commands"][0]["cfg"]
    send_cfg = payload["tests"][0]["commands"][0]["cfg"]
    assert_cfg = payload["tests"][0]["commands"][1]["cfg"]

    assert init_cfg["definitionId"]
    assert send_cfg["sourceConstantRef"]["definitionId"] == init_cfg["definitionId"]
    assert send_cfg["resultConstant"]["name"] == "publishResult"
    assert send_cfg["resultConstant"]["definitionId"]
    assert assert_cfg["actualConstantRef"]["definitionId"] == send_cfg["resultConstant"]["definitionId"]
