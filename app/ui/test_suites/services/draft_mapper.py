from uuid import uuid4


def new_ui_key() -> str:
    return uuid4().hex[:10]


def build_test_suite_draft(payload: dict | None) -> dict:
    source = payload if isinstance(payload, dict) else {}
    hooks_map: dict[str, dict] = {}
    for hook in source.get("hooks") or []:
        if not isinstance(hook, dict):
            continue
        hook_phase = str(hook.get("hook_phase") or "").strip()
        if not hook_phase:
            continue
        hooks_map[hook_phase] = {
            **hook,
            "operations": list(hook.get("commands") or hook.get("operations") or []),
            "_ui_key": str(hook.get("_ui_key") or new_ui_key()),
        }

    tests = []
    for idx, test in enumerate(source.get("tests") or [], start=1):
        if not isinstance(test, dict):
            continue
        tests.append(
            {
                **test,
                "position": int(test.get("position") or idx),
                "operations": list(test.get("commands") or test.get("operations") or []),
                "_ui_key": str(test.get("_ui_key") or new_ui_key()),
            }
        )

    return {
        "id": source.get("id"),
        "description": str(source.get("description") or ""),
        "hooks": hooks_map,
        "tests": tests,
    }


def draft_to_test_suite_payload(draft: dict) -> dict:
    def _serialize_item(item: dict) -> dict:
        operations = []
        for op_idx, operation in enumerate(item.get("operations") or [], start=1):
            cfg = operation.get("configuration_json")
            operations.append(
                {
                    "order": int(operation.get("order") or op_idx),
                    "description": str(operation.get("description") or ""),
                    "cfg": cfg if isinstance(cfg, dict) else {},
                }
            )

        payload = {
            "kind": str(item.get("kind") or "test"),
            "description": str(item.get("description") or ""),
            "on_failure": str(item.get("on_failure") or "ABORT"),
            "commands": operations,
        }
        hook_phase = str(item.get("hook_phase") or "").strip()
        if hook_phase:
            payload["hook_phase"] = hook_phase
        return payload

    hooks_payload = []
    hooks = draft.get("hooks") or {}
    if isinstance(hooks, dict):
        for phase, item in hooks.items():
            if not isinstance(item, dict):
                continue
            item["hook_phase"] = phase
            item["kind"] = "hook"
            hooks_payload.append(_serialize_item(item))

    tests_payload = []
    for position, item in enumerate(draft.get("tests") or [], start=1):
        if not isinstance(item, dict):
            continue
        item["position"] = position
        item["kind"] = "test"
        tests_payload.append(_serialize_item(item))

    return {
        "description": str(draft.get("description") or ""),
        "hooks": hooks_payload,
        "tests": tests_payload,
    }
