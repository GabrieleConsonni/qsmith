# Elaborations Test Matrix

| Capability | Test Type | Coverage |
| --- | --- | --- |
| Supported FastAPI route inventory | Integration | `test/integration/test_elaborations_api_inventory.py` |
| SSE history replay and finish | Service/Unit | `test/alembic/services/test_suite_execution_sse.py` |
| SSE heartbeat and subscriber cleanup | Service/Unit | `test/alembic/services/test_suite_execution_sse.py` |
| SSE drop warning on full queue | Service/Unit | `test/alembic/services/test_suite_execution_sse.py` |
| Suite runtime test selection | Service/Unit | `test/alembic/services/test_suite_execution_sse.py`, `test/unit/test_elaborations_runtime_helpers.py` |
| Test suite runtime item selection | Unit | `test/unit/test_elaborations_runtime_helpers.py` |
| Assert evaluator dispatch | Unit | `test/unit/test_assert_evaluator_composite.py` |
| Assert operations end-to-end | Integration/Service | `test/alembic/services/test_operation_executors.py` |
| Test executors for json-array/db/queue/data/sleep | Integration/Service | `test/alembic/services/test_test_executors.py` |
| Operation catalog API persistence | Integration/Service | `test/alembic/services/test_operation_executors.py` |
| Test suite API + runtime persistence | Integration/Service | `test/alembic/services/test_test_suite_runtime.py` |

## Explicitly Pruned Surfaces
- Suite CRUD API
- Test CRUD API
- Suite execution history API
- Suite pages in Streamlit UI
- Standalone test editor UI
