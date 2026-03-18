from __future__ import annotations

from copy import deepcopy
from uuid import uuid4


SUITE_SECTION_TEST = "test"
SUITE_SECTION_BEFORE_ALL = "beforeAll"
SUITE_SECTION_BEFORE_EACH = "beforeEach"
SUITE_SECTION_AFTER_EACH = "afterEach"
SUITE_SECTION_AFTER_ALL = "afterAll"

_READABLE_SCOPES: dict[str, set[str]] = {
    SUITE_SECTION_BEFORE_ALL: {"runEnvelope", "result"},
    SUITE_SECTION_BEFORE_EACH: {"runEnvelope", "global", "result"},
    SUITE_SECTION_TEST: {"runEnvelope", "global", "local", "result"},
    SUITE_SECTION_AFTER_EACH: {"runEnvelope", "global", "local", "result"},
    SUITE_SECTION_AFTER_ALL: {"runEnvelope", "global", "result"},
}


def new_ui_key() -> str:
    return uuid4().hex[:10]


def _new_definition_id() -> str:
    return str(uuid4())


def _normalize_cfg(value: object) -> dict:
    return deepcopy(value) if isinstance(value, dict) else {}


def _normalize_token(value: object) -> str:
    return str(value or "").strip()


def _command_code(cfg: dict) -> str:
    return _normalize_token(cfg.get("commandCode") or cfg.get("command_code"))


def _definition_path(scope: str, name: str) -> str:
    return f"$.{scope}.constants.{name}"


def _extract_scope_name(path_value: object) -> tuple[str | None, str | None]:
    raw = _normalize_token(path_value)
    if not raw:
        return None, None
    if raw.startswith("$."):
        raw = raw[2:]
    elif raw.startswith("$"):
        raw = raw[1:].lstrip(".")
    parts = [part for part in raw.split(".") if part]
    if len(parts) >= 3 and parts[1] == "constants":
        return parts[0], parts[-1]
    return None, None


def _constant_ref_id(value: object) -> str:
    if isinstance(value, dict):
        return _normalize_token(value.get("definitionId") or value.get("definition_id"))
    return ""


def _result_constant(value: object) -> dict:
    return deepcopy(value) if isinstance(value, dict) else {}


def _definition_from_init(cfg: dict, command_order: int) -> dict | None:
    definition_id = _normalize_token(cfg.get("definitionId") or cfg.get("definition_id"))
    name = _normalize_token(cfg.get("name") or cfg.get("key"))
    context = _normalize_token(cfg.get("context") or cfg.get("scope"))
    if not definition_id or not name or not context:
        return None
    return {
        "definitionId": definition_id,
        "name": name,
        "context_scope": context,
        "value_type": _normalize_token(cfg.get("sourceType") or cfg.get("source_type") or "raw") or "raw",
        "declared_at_order": int(command_order),
        "deleted_at_order": None,
    }


def _definition_from_result(cfg: dict, command_order: int) -> dict | None:
    result_constant = _result_constant(cfg.get("resultConstant") or cfg.get("result_constant"))
    definition_id = _normalize_token(result_constant.get("definitionId") or result_constant.get("definition_id"))
    name = _normalize_token(result_constant.get("name"))
    if not definition_id or not name:
        return None
    return {
        "definitionId": definition_id,
        "name": name,
        "context_scope": "result",
        "value_type": _normalize_token(result_constant.get("valueType") or result_constant.get("value_type") or "json")
        or "json",
        "declared_at_order": int(command_order),
        "deleted_at_order": None,
    }


def _clone_visible_definitions(definitions: dict[str, dict] | None) -> dict[str, dict]:
    return {definition_id: dict(definition) for definition_id, definition in (definitions or {}).items()}


def _carry_over_definitions(definitions: dict[str, dict] | None) -> dict[str, dict]:
    carried: dict[str, dict] = {}
    for definition_id, definition in (definitions or {}).items():
        if definition.get("deleted_at_order") is not None:
            continue
        carried[definition_id] = {
            **definition,
            "declared_at_order": 0,
        }
    return carried


def _visible_definitions(
    definitions: dict[str, dict],
    *,
    section_type: str,
    command_order: int,
) -> list[dict]:
    result: list[dict] = []
    readable_scopes = _READABLE_SCOPES.get(section_type, set())
    for definition in definitions.values():
        if definition.get("context_scope") not in readable_scopes:
            continue
        if int(definition.get("declared_at_order") or 0) >= int(command_order):
            continue
        deleted_at_order = definition.get("deleted_at_order")
        if deleted_at_order is not None and int(deleted_at_order) <= int(command_order):
            continue
        result.append(definition)
    result.sort(key=lambda item: int(item.get("declared_at_order") or 0))
    return result


def _find_definition_by_scope_name(
    definitions: dict[str, dict],
    *,
    section_type: str,
    command_order: int,
    scope: str | None,
    name: str | None,
) -> dict | None:
    normalized_scope = _normalize_token(scope)
    normalized_name = _normalize_token(name)
    if not normalized_scope or not normalized_name:
        return None
    matches = [
        definition
        for definition in _visible_definitions(
            definitions,
            section_type=section_type,
            command_order=command_order,
        )
        if definition.get("context_scope") == normalized_scope and definition.get("name") == normalized_name
    ]
    return matches[-1] if matches else None


def _find_definition_by_path(
    definitions: dict[str, dict],
    *,
    section_type: str,
    command_order: int,
    path_value: object,
) -> dict | None:
    scope, name = _extract_scope_name(path_value)
    return _find_definition_by_scope_name(
        definitions,
        section_type=section_type,
        command_order=command_order,
        scope=scope,
        name=name,
    )


def _find_definition_by_id(
    definitions: dict[str, dict],
    *,
    section_type: str,
    command_order: int,
    definition_id: str,
) -> dict | None:
    for definition in _visible_definitions(
        definitions,
        section_type=section_type,
        command_order=command_order,
    ):
        if definition.get("definitionId") == definition_id:
            return definition
    return None


def _find_definition_by_name(
    definitions: dict[str, dict],
    *,
    section_type: str,
    command_order: int,
    name: str,
) -> dict | None:
    for scope in ("local", "global", "runEnvelope", "result"):
        definition = _find_definition_by_scope_name(
            definitions,
            section_type=section_type,
            command_order=command_order,
            scope=scope,
            name=name,
        )
        if definition is not None:
            return definition
    return None


def _serialize_result_constant(cfg: dict) -> dict | None:
    result_constant = _result_constant(cfg.get("resultConstant") or cfg.get("result_constant"))
    if result_constant:
        definition_id = _normalize_token(result_constant.get("definitionId") or result_constant.get("definition_id"))
        name = _normalize_token(result_constant.get("name"))
        value_type = _normalize_token(result_constant.get("valueType") or result_constant.get("value_type") or "json") or "json"
        if definition_id and name:
            return {
                "definitionId": definition_id,
                "name": name,
                "valueType": value_type,
            }

    scope, name = _extract_scope_name(cfg.get("result_target") or cfg.get("resultTarget"))
    if scope != "result" or not name:
        return None

    return {
        "definitionId": _new_definition_id(),
        "name": name,
        "valueType": "json",
    }


def _hydrate_operation_cfg(cfg: dict, definitions: dict[str, dict], section_type: str, command_order: int) -> dict:
    hydrated = deepcopy(cfg)
    command_code = _command_code(hydrated)

    if command_code == "deleteConstant":
        definition_id = _constant_ref_id(hydrated.get("targetConstantRef") or hydrated.get("target_constant_ref"))
        definition = _find_definition_by_id(
            definitions,
            section_type=section_type,
            command_order=command_order,
            definition_id=definition_id,
        )
        if definition is not None:
            hydrated.setdefault("name", definition.get("name"))
            hydrated.setdefault("context", definition.get("context_scope"))
            hydrated.setdefault("scope", definition.get("context_scope"))

    source_definition_id = _constant_ref_id(hydrated.get("sourceConstantRef") or hydrated.get("source_constant_ref"))
    if source_definition_id and not _normalize_token(hydrated.get("source")):
        definition = _find_definition_by_id(
            definitions,
            section_type=section_type,
            command_order=command_order,
            definition_id=source_definition_id,
        )
        if definition is not None:
            hydrated["source"] = _definition_path(definition["context_scope"], definition["name"])

    actual_definition_id = _constant_ref_id(hydrated.get("actualConstantRef") or hydrated.get("actual_constant_ref"))
    if actual_definition_id and not hydrated.get("actual"):
        definition = _find_definition_by_id(
            definitions,
            section_type=section_type,
            command_order=command_order,
            definition_id=actual_definition_id,
        )
        if definition is not None:
            hydrated["actual"] = _definition_path(definition["context_scope"], definition["name"])

    constant_refs = hydrated.get("constantRefs") or hydrated.get("constant_refs") or []
    if constant_refs and not hydrated.get("constants"):
        constant_names: list[str] = []
        for item in constant_refs:
            definition_id = _constant_ref_id(item)
            definition = _find_definition_by_id(
                definitions,
                section_type=section_type,
                command_order=command_order,
                definition_id=definition_id,
            )
            if definition is not None:
                constant_names.append(str(definition.get("name") or ""))
        if constant_names:
            hydrated["constants"] = constant_names

    result_constant = _serialize_result_constant(hydrated)
    if result_constant is not None and not _normalize_token(hydrated.get("result_target") or hydrated.get("resultTarget")):
        hydrated["result_target"] = _definition_path("result", result_constant["name"])

    return hydrated


def _serialize_operation_cfg(cfg: dict, definitions: dict[str, dict], section_type: str, command_order: int) -> dict:
    serialized = deepcopy(cfg)
    command_code = _command_code(serialized)

    if command_code == "initConstant":
        serialized["definitionId"] = _normalize_token(serialized.get("definitionId") or serialized.get("definition_id")) or _new_definition_id()

    if command_code == "deleteConstant":
        serialized.pop("targetConstantRef", None)
        serialized.pop("target_constant_ref", None)
        definition = _find_definition_by_scope_name(
            definitions,
            section_type=section_type,
            command_order=command_order,
            scope=serialized.get("context") or serialized.get("scope"),
            name=serialized.get("name") or serialized.get("key"),
        )
        if definition is not None:
            serialized["targetConstantRef"] = {"definitionId": definition["definitionId"]}

    if command_code in {"sendMessageQueue", "saveTable", "exportDataset"}:
        serialized.pop("sourceConstantRef", None)
        serialized.pop("source_constant_ref", None)
        definition = _find_definition_by_path(
            definitions,
            section_type=section_type,
            command_order=command_order,
            path_value=serialized.get("source"),
        )
        if definition is not None:
            serialized["sourceConstantRef"] = {"definitionId": definition["definitionId"]}

    if command_code in {
        "jsonEquals",
        "jsonEmpty",
        "jsonNotEmpty",
        "jsonContains",
        "jsonArrayEquals",
        "jsonArrayEmpty",
        "jsonArrayNotEmpty",
        "jsonArrayContains",
    }:
        serialized.pop("actualConstantRef", None)
        serialized.pop("actual_constant_ref", None)
        definition = _find_definition_by_path(
            definitions,
            section_type=section_type,
            command_order=command_order,
            path_value=serialized.get("actual"),
        )
        if definition is not None:
            serialized["actualConstantRef"] = {"definitionId": definition["definitionId"]}

    if command_code == "runSuite":
        serialized.pop("constantRefs", None)
        serialized.pop("constant_refs", None)
        constant_refs: list[dict[str, str]] = []
        for constant_name in serialized.get("constants") or []:
            definition = _find_definition_by_name(
                definitions,
                section_type=section_type,
                command_order=command_order,
                name=str(constant_name or ""),
            )
            if definition is not None:
                constant_refs.append({"definitionId": definition["definitionId"]})
        if constant_refs:
            serialized["constantRefs"] = constant_refs

    result_constant = _serialize_result_constant(serialized)
    if result_constant is not None:
        serialized["resultConstant"] = result_constant

    return serialized


def _apply_post_command_definition_updates(cfg: dict, definitions: dict[str, dict], command_order: int) -> None:
    command_code = _command_code(cfg)
    if command_code == "deleteConstant":
        definition_id = _constant_ref_id(cfg.get("targetConstantRef") or cfg.get("target_constant_ref"))
        if definition_id and definition_id in definitions:
            definitions[definition_id] = {
                **definitions[definition_id],
                "deleted_at_order": int(command_order),
            }
        return

    declared_constant = _definition_from_init(cfg, command_order)
    if declared_constant is not None:
        definitions[declared_constant["definitionId"]] = declared_constant

    result_constant = _definition_from_result(cfg, command_order)
    if result_constant is not None:
        definitions[result_constant["definitionId"]] = result_constant


def _normalize_operations_for_draft(
    operations_source: list[dict] | None,
    *,
    section_type: str,
    initial_definitions: dict[str, dict],
) -> tuple[list[dict], dict[str, dict]]:
    definitions = _carry_over_definitions(initial_definitions)
    normalized_operations: list[dict] = []
    for op_idx, operation in enumerate(operations_source or [], start=1):
        if not isinstance(operation, dict):
            continue
        cfg = _normalize_cfg(operation.get("configuration_json") or operation.get("cfg"))
        command_order = int(operation.get("order") or op_idx)
        hydrated_cfg = _hydrate_operation_cfg(cfg, definitions, section_type, command_order)
        normalized_operation = {
            **operation,
            "order": command_order,
            "configuration_json": hydrated_cfg,
            "_ui_key": str(operation.get("_ui_key") or new_ui_key()),
        }
        normalized_operations.append(normalized_operation)
        _apply_post_command_definition_updates(hydrated_cfg, definitions, command_order)
    return normalized_operations, definitions


def _serialize_operations_for_payload(
    operations_source: list[dict] | None,
    *,
    section_type: str,
    initial_definitions: dict[str, dict],
) -> tuple[list[dict], dict[str, dict]]:
    definitions = _carry_over_definitions(initial_definitions)
    commands_payload: list[dict] = []
    for op_idx, operation in enumerate(operations_source or [], start=1):
        if not isinstance(operation, dict):
            continue
        cfg = _normalize_cfg(operation.get("configuration_json") or operation.get("cfg"))
        command_order = int(operation.get("order") or op_idx)
        serialized_cfg = _serialize_operation_cfg(cfg, definitions, section_type, command_order)
        commands_payload.append(
            {
                "order": command_order,
                "description": str(operation.get("description") or ""),
                "cfg": serialized_cfg,
            }
        )
        _apply_post_command_definition_updates(serialized_cfg, definitions, command_order)
    return commands_payload, definitions


def _section_type_for_phase(hook_phase: str) -> str:
    mapping = {
        "before-all": SUITE_SECTION_BEFORE_ALL,
        "before-each": SUITE_SECTION_BEFORE_EACH,
        "after-each": SUITE_SECTION_AFTER_EACH,
        "after-all": SUITE_SECTION_AFTER_ALL,
    }
    return mapping.get(str(hook_phase or "").strip(), SUITE_SECTION_TEST)


def build_test_suite_draft(payload: dict | None) -> dict:
    source = payload if isinstance(payload, dict) else {}
    hooks_map: dict[str, dict] = {}

    raw_hooks = {
        str(hook.get("hook_phase") or "").strip(): hook
        for hook in source.get("hooks") or []
        if isinstance(hook, dict) and str(hook.get("hook_phase") or "").strip()
    }

    before_all_defs: dict[str, dict] = {}
    before_each_defs: dict[str, dict] = {}

    before_all_hook = raw_hooks.get("before-all")
    if isinstance(before_all_hook, dict):
        operations, before_all_defs = _normalize_operations_for_draft(
            list(before_all_hook.get("commands") or before_all_hook.get("operations") or []),
            section_type=SUITE_SECTION_BEFORE_ALL,
            initial_definitions={},
        )
        hooks_map["before-all"] = {
            **before_all_hook,
            "operations": operations,
            "_ui_key": str(before_all_hook.get("_ui_key") or new_ui_key()),
        }
    before_each_defs = _clone_visible_definitions(before_all_defs)

    before_each_hook = raw_hooks.get("before-each")
    if isinstance(before_each_hook, dict):
        operations, before_each_defs = _normalize_operations_for_draft(
            list(before_each_hook.get("commands") or before_each_hook.get("operations") or []),
            section_type=SUITE_SECTION_BEFORE_EACH,
            initial_definitions=before_all_defs,
        )
        hooks_map["before-each"] = {
            **before_each_hook,
            "operations": operations,
            "_ui_key": str(before_each_hook.get("_ui_key") or new_ui_key()),
        }

    tests = []
    for idx, test in enumerate(source.get("tests") or [], start=1):
        if not isinstance(test, dict):
            continue
        operations, _ = _normalize_operations_for_draft(
            list(test.get("commands") or test.get("operations") or []),
            section_type=SUITE_SECTION_TEST,
            initial_definitions=before_each_defs,
        )
        tests.append(
            {
                **test,
                "position": int(test.get("position") or idx),
                "operations": operations,
                "_ui_key": str(test.get("_ui_key") or new_ui_key()),
            }
        )

    after_each_hook = raw_hooks.get("after-each")
    if isinstance(after_each_hook, dict):
        operations, _ = _normalize_operations_for_draft(
            list(after_each_hook.get("commands") or after_each_hook.get("operations") or []),
            section_type=SUITE_SECTION_AFTER_EACH,
            initial_definitions=before_each_defs,
        )
        hooks_map["after-each"] = {
            **after_each_hook,
            "operations": operations,
            "_ui_key": str(after_each_hook.get("_ui_key") or new_ui_key()),
        }

    after_all_hook = raw_hooks.get("after-all")
    if isinstance(after_all_hook, dict):
        operations, _ = _normalize_operations_for_draft(
            list(after_all_hook.get("commands") or after_all_hook.get("operations") or []),
            section_type=SUITE_SECTION_AFTER_ALL,
            initial_definitions=before_all_defs,
        )
        hooks_map["after-all"] = {
            **after_all_hook,
            "operations": operations,
            "_ui_key": str(after_all_hook.get("_ui_key") or new_ui_key()),
        }

    return {
        "id": source.get("id"),
        "description": str(source.get("description") or ""),
        "hooks": hooks_map,
        "tests": tests,
    }


def draft_to_test_suite_payload(draft: dict) -> dict:
    def _serialize_item(item: dict, *, section_type: str, initial_definitions: dict[str, dict]) -> tuple[dict, dict[str, dict]]:
        commands, resulting_definitions = _serialize_operations_for_payload(
            list(item.get("operations") or []),
            section_type=section_type,
            initial_definitions=initial_definitions,
        )
        payload = {
            "kind": str(item.get("kind") or "test"),
            "description": str(item.get("description") or ""),
            "on_failure": str(item.get("on_failure") or "ABORT"),
            "commands": commands,
        }
        hook_phase = str(item.get("hook_phase") or "").strip()
        if hook_phase:
            payload["hook_phase"] = hook_phase
        return payload, resulting_definitions

    hooks_payload = []
    hooks = draft.get("hooks") or {}
    before_all_defs: dict[str, dict] = {}
    before_each_defs: dict[str, dict] = {}

    if isinstance(hooks, dict):
        before_all_item = hooks.get("before-all")
        if isinstance(before_all_item, dict):
            before_all_item["hook_phase"] = "before-all"
            before_all_item["kind"] = "hook"
            payload, before_all_defs = _serialize_item(
                before_all_item,
                section_type=SUITE_SECTION_BEFORE_ALL,
                initial_definitions={},
            )
            hooks_payload.append(payload)
        before_each_defs = _clone_visible_definitions(before_all_defs)

        before_each_item = hooks.get("before-each")
        if isinstance(before_each_item, dict):
            before_each_item["hook_phase"] = "before-each"
            before_each_item["kind"] = "hook"
            payload, before_each_defs = _serialize_item(
                before_each_item,
                section_type=SUITE_SECTION_BEFORE_EACH,
                initial_definitions=before_all_defs,
            )
            hooks_payload.append(payload)

    tests_payload = []
    for position, item in enumerate(draft.get("tests") or [], start=1):
        if not isinstance(item, dict):
            continue
        item["position"] = position
        item["kind"] = "test"
        payload, _ = _serialize_item(
            item,
            section_type=SUITE_SECTION_TEST,
            initial_definitions=before_each_defs,
        )
        tests_payload.append(payload)

    if isinstance(hooks, dict):
        after_each_item = hooks.get("after-each")
        if isinstance(after_each_item, dict):
            after_each_item["hook_phase"] = "after-each"
            after_each_item["kind"] = "hook"
            payload, _ = _serialize_item(
                after_each_item,
                section_type=SUITE_SECTION_AFTER_EACH,
                initial_definitions=before_each_defs,
            )
            hooks_payload.append(payload)

        after_all_item = hooks.get("after-all")
        if isinstance(after_all_item, dict):
            after_all_item["hook_phase"] = "after-all"
            after_all_item["kind"] = "hook"
            payload, _ = _serialize_item(
                after_all_item,
                section_type=SUITE_SECTION_AFTER_ALL,
                initial_definitions=before_all_defs,
            )
            hooks_payload.append(payload)

    return {
        "description": str(draft.get("description") or ""),
        "hooks": hooks_payload,
        "tests": tests_payload,
    }
