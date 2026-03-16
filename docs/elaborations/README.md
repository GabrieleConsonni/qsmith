# Elaborations Technical Overview

## Scope
- Supported HTTP surfaces:
  - `/elaborations/test-suite`
  - `/elaborations/test-suite-execution`
  - `/elaborations/execution/{execution_id}/events`
- Removed standalone surfaces:
  - suite CRUD/execution endpoints
  - test CRUD endpoints
  - suite execution history endpoints
  - suite test-operation endpoints

## Runtime Architecture
- `test_suites_api` manages suite definitions and starts asynchronous suite execution threads.
- `test_suite_executions_api` exposes persisted suite execution history.
- `execution_events_api` streams runtime events through an in-memory SSE bus.
- Internal suite runtime remains available only as an application service, mainly for `run-suite` operations and execution orchestration reuse.

## Main Data Flow
1. UI editors load datasource/broker context from `app/ui/elaborations_shared`.
2. Suite execution starts through `TestSuiteExecutorThread`.
3. Runtime binds execution context and run context.
4. Suite items execute operations through `operation_executor_composite`.
5. Events are published on the SSE bus and execution rows are persisted in Postgres.

## Key Modules
- `app/elaborations/api`: supported FastAPI routes for test suites, suite executions, SSE.
- `app/elaborations/services/operations`: operation dispatch, policy validation, runtime execution.
- `app/elaborations/services/test_suites`: asynchronous suite execution and hook/test orchestration.
- `app/elaborations/services/suites`: internal suite runtime, run context, execution event bus.
- `app/ui/elaborations_shared`: shared Streamlit datasource/broker loaders, state keys, operation editor reused by suite/mock-server UIs.

## Testing Notes
- Route wiring is validated through an OpenAPI/TestClient inventory test.
- Runtime and persistence tests use Postgres Testcontainers.
- Pure helper coverage exists for evaluator dispatch and runtime target-selection helpers.
