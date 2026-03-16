# Qsmith - Contesto Progetto per Codex

## Panoramica
Qsmith e un'applicazione per test e orchestrazione di flussi su broker SQS, datasource e test suite.
Il progetto e composto da:
- backend FastAPI
- UI Streamlit multipage

Domini principali:
- broker/queue (send, receive, ack, metriche)
- datasource JSON array e datasource tabellari database
- test suite (hook + test + operation) con esecuzioni persistite
- mock server API/queue con attivazione runtime
- logs applicativi

## Stack tecnologico
- Python 3.13
- FastAPI + Pydantic
- SQLAlchemy 2 + Alembic
- PostgreSQL
- ElasticMQ (SQS locale)
- Streamlit
- Docker / Docker Compose
- Testcontainers (test backend)

## Mappa repository
- `app/` codice backend + UI
- `app/main.py` entrypoint API FastAPI
- `app/ui/Qsmith.py` entrypoint UI Streamlit
- `alembic/` migrazioni DB
- `elasticmq/` compose/config ElasticMQ locale
- `docker/` Dockerfile API/UI
- `docs/` documentazione
  - `docs/TASK.md` backlog QSM
  - `docs/SPEC.md` specifica funzionale
  - `docs/STORY_INDEX.md` indice storie
  - `docs/stories/` storie QSM
  - `docs/bugs/` bug log (formato `QSMB-XXX`)

## Entry point e bootstrap
In `app/main.py` all'avvio:
1. carica `.env`
2. esegue migrazioni Alembic
3. inizializza ElasticMQ (`init_elasticmq`)
4. registra router API
5. a startup bootstrap dei mock server attivi (`MockServerRuntimeRegistry.bootstrap_active_servers()`)

## UI Streamlit
Entry point: `app/ui/Qsmith.py`

Pagine principali:
- `app/ui/pages/Home.py`
- `app/ui/pages/Brokers.py`
- `app/ui/pages/DatabaseConnections.py`
- `app/ui/pages/DatabaseDataSources.py`
- `app/ui/pages/MockServers.py`
- `app/ui/pages/MockServerEditor.py`
- `app/ui/pages/Queues.py`
- `app/ui/pages/QueueDetails.py`
- `app/ui/pages/JsonArray.py`
- `app/ui/pages/TestSuites.py`
- `app/ui/pages/SuiteEditor.py`
- `app/ui/pages/Logs.py`
- `app/ui/pages/Tools.py`

Organizzazione UI modulare gia presente in package dedicati:
- `app/ui/brokers`
- `app/ui/database_connections`
- `app/ui/database_datasources`
- `app/ui/json_arrays`
- `app/ui/mock_servers`
- `app/ui/suites` (componenti operation legacy/shared)
- `app/ui/test_suites`
- `app/ui/queues`

## Router API principali
- `/broker`
  - connessioni broker
  - queue del broker
  - messaggi queue (send/receive/ack/test)
- `/data-source`
  - json-array datasource
  - database table datasource
- `/database`
  - database connections + test + metadata oggetti + preview
- `/elaborations`
  - test suites
  - suite_items / suite_item_commands (snapshot)
  - test suite executions
  - SSE runtime: `/elaborations/execution/{execution_id}/events`
- `/mock-server`
  - CRUD mock server + activate/deactivate
- runtime mock API
  - route dinamiche sotto `/mock/{server_endpoint}/...`
- `/logs`
- `/json_utils`

## Modello dati (alto livello)
- `json_payloads` configurazioni JSON tipizzate
- `queues` configurazioni queue per broker
- `test_suites` anagrafica suite
- `suite_items` snapshot funzionale di test e hook
- `suite_item_commands` snapshot funzionale operation sull'item
- `test_suite_executions`, `suite_item_executions`, `suite_item_command_executions`
- `mock_servers`, `mock_server_apis`, `ms_api_commands`
- `mock_server_queues`, `ms_queue_commands`
- `logs`

Nota: il runtime suite e mock usa snapshot contestuali (`suite_items`/`suite_item_commands`, `ms_api_commands`, `ms_queue_commands`), senza catalogo condiviso `commands`.

## Configurazione ambiente
Valori esempio `.env`:
```env
DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<db>
HOST_IP=<host>
```

Non inserire credenziali reali nei documenti.

## Avvio e stop
Avvio stack API + UI:
```bash
docker compose -f docker-compose.yml up --build -d
```

Stop:
```bash
docker compose -f docker-compose.yml down
```

Script Windows alternativo:
```bat
docker-run-dev.bat
```

## Servizi e URL utili
Da `docker-compose.yml`:
- API `qsmith`: `http://localhost:9082`
- UI `qsmith-ui`: `http://localhost:8501`
- Debugpy API: `localhost:5678`

Altri endpoint:
- Swagger: `http://localhost:9082/docs`
- OpenAPI: `http://localhost:9082/openapi.json`

ElasticMQ locale (opzionale, compose dedicato in `elasticmq/`):
- SQS endpoint: `http://localhost:9324`
- Console: `http://localhost:9325`

## Test
Comando principale:
```bash
pytest test
```

I test usano Testcontainers, quindi Docker deve essere disponibile.

## Regole operative docs
Quando cambia il comportamento funzionale o il piano di lavoro:
- aggiornare `docs/SPEC.md`
- aggiornare `docs/stories/QSM-*.md`
- aggiornare `docs/stories/STORY_INDEX.md` se cambiano le storie
- aggiornare `docs/CODEX_CONTEXT.md` se cambia il contesto progetto

