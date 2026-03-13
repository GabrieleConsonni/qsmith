from typing import Any

from elaborations.services.operations.operation_contract_registry import (
    OperationContract,
    get_operation_contract,
)
from elaborations.services.operations.operation_scope import (
    SCOPE_MOCK_PRE_RESPONSE,
    SCOPE_MOCK_RESPONSE,
    SCOPE_TEST,
)
from elaborations.services.scenarios.run_context import extract_context_root


def _collect_target_paths(cfg: Any) -> list[str]:
    targets: list[str] = []
    target = getattr(cfg, "target", None)
    if isinstance(target, str) and target.strip():
        targets.append(target)
    result_target = getattr(cfg, "result_target", None)
    if isinstance(result_target, str) and result_target.strip():
        targets.append(result_target)
    return targets


def _validate_scope_rules(contract: OperationContract, execution_scope: str | None):
    if not execution_scope:
        return
    if execution_scope not in contract.supported_scopes:
        raise ValueError(
            f"Operation '{contract.name}' is not allowed in scope '{execution_scope}'."
        )
    if execution_scope == SCOPE_MOCK_PRE_RESPONSE:
        if contract.side_effects:
            raise ValueError(
                f"Operation '{contract.name}' has side effects and cannot run in mock.preResponse."
            )
        if contract.async_allowed:
            raise ValueError(
                f"Operation '{contract.name}' is async-enabled and cannot run in mock.preResponse."
            )


def _validate_target_roots(targets: list[str], execution_scope: str | None):
    for target in targets:
        root = extract_context_root(target)
        if root is None:
            raise ValueError(
                f"Unsupported target path '{target}'. Use $.global, $.local, $.artifacts or $.response."
            )
        if execution_scope == SCOPE_TEST and root == "global":
            raise ValueError("Global context is immutable during test execution.")
        if root == "response" and execution_scope != SCOPE_MOCK_RESPONSE:
            raise ValueError("Response draft can be written only in mock.response scope.")


def validate_operation_policy(cfg: Any, execution_scope: str | None) -> OperationContract:
    operation_type = str(getattr(cfg, "operationType", "") or "").strip()
    contract = get_operation_contract(operation_type)
    if contract is None:
        raise ValueError(f"No operation contract found for operation type '{operation_type}'.")
    _validate_scope_rules(contract, execution_scope)
    _validate_target_roots(_collect_target_paths(cfg), execution_scope)
    return contract
