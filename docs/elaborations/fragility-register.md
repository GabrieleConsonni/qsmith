# Elaborations Fragility Register

## Current Fragilities

### Daemon execution threads
- Area: suite and suite runtime threads
- Risk: no explicit registry, cancel, or back-pressure management
- Observation points:
  - thread start/finish logs
  - persisted execution rows stuck in `running`
  - missing terminal SSE event

### In-memory SSE bus
- Area: `execution_event_bus`
- Risk: subscriber queues are bounded and best-effort; slow consumers can lose events
- Observation points:
  - warning logs for dropped events
  - heartbeat without corresponding progress updates
  - high number of short-lived subscribers

### Internal suite runtime without public CRUD surface
- Area: `run-suite` operation and suite execution services
- Risk: runtime remains coupled to suite persistence, but no supported UI/API manages those definitions anymore
- Observation points:
  - failed `run-suite` operations due to missing suite ids
  - orphaned suite records not discoverable from supported UI

### Test environment dependency on containers
- Area: integration/service tests
- Risk: Postgres/Testcontainers availability gates meaningful verification
- Observation points:
  - skipped tests due to Docker/Testcontainers startup failure
  - missing local Python dependencies despite declared requirements

### Log subject granularity
- Area: suite execution logging
- Risk: suite runtime still logs under `SUITE_EXECUTION`, which weakens filtering and diagnostics
- Observation points:
  - mixed suite/suite log searches
  - ambiguous subject values in operational logs

## Suggested Follow-ups
- Add execution metrics or counters if a monitoring stack is introduced.
- Decide whether internal suite persistence should remain a supported backend capability or be removed in a later pass.
- Introduce a dedicated log subject type for test suite execution when log taxonomy changes are allowed.

