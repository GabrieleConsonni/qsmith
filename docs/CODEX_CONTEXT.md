# Qsmith - Contesto Progetto per Codex

**Panoramica**
Qsmith e un queue manager composto da backend FastAPI e UI Streamlit. Gestisce broker SQS (ElasticMQ/Amazon), queue, connessioni database, sorgenti dati JSON array/table e orchestrazione di scenari (step/operations). Usa PostgreSQL come storage principale e puo inizializzare le queue ElasticMQ all'avvio.

**Stack Tecnologico**
- Python 3.13
- FastAPI, Pydantic
- SQLAlchemy 2 + Alembic
- PostgreSQL
- ElasticMQ (emulatore SQS in locale)
- Docker, Testcontainers
- Streamlit (UI)

**Mappa Repository**
- `app/` codice applicazione backend FastAPI
- `app/ui/` UI web Streamlit (multipage)
- `alembic/` migrazioni database
- `elasticmq/` docker-compose e config per ElasticMQ
- `docker/` Dockerfile API/UI
- `docs/` documentazione

**Entry Point e Flusso di Avvio**
- `app/main.py`:
  - carica `.env`
  - esegue migrazioni Alembic all avvio
  - inizializza ElasticMQ creando code per i broker `elasticmq`
  - registra router API e handler di eccezioni

**UI Streamlit**
- Entry point: `app/ui/Qsmith.py`
- Pagine principali:
  - `app/ui/pages/Brokers.py`
  - `app/ui/pages/DatabaseConnections.py`
  - `app/ui/pages/DAtabaseDatasources.py`
  - `app/ui/pages/JsonArray.py`
  - `app/ui/pages/Logs.py`
  - `app/ui/pages/QueueDetails.py`
  - `app/ui/pages/Queues.py`
  - `app/ui/pages/ScenarioEditor.py`
  - `app/ui/pages/Scenarios.py`
  - `app/ui/pages/Tools.py`

**Router API principali**
- `/broker` (connection e queue operations)
- `/data-source` (json-array, database datasources)
- `/database` (database connections, test, objects metadata, preview)
- `/elaborations` (scenari, step, operations)
  - include anche stream runtime SSE: `/elaborations/execution/{execution_id}/events`
- `/logs`
- `/json_utils`

**Concetti Chiave (Modello Dati)**
- `json_payloads` config JSON generiche con tipo (`BROKER_CONNECTION`, ecc.)
- `queues` configurazioni code legate a un broker
- `operations` definizioni di operazioni con `operation_type` e configurazione JSON
- `steps` definizioni di step con `step_type` e configurazione JSON
- `scenarios` elenco scenari
- `scenario_steps` snapshot degli step usati nello scenario (code/description/type/configuration_json + ordine + on_failure)
- `step_operations` snapshot delle operazioni usate nel singolo scenario_step (code/description/type/configuration_json + ordine)
- `logs` eventi applicativi

**Configurazione Ambiente**
File `.env` (valori di esempio, non usare credenziali reali nei documenti):
```
DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<db>
HOST_IP=<host>
```
Nota: il percorso operativo standard e via Docker.

**Avvio (Obbligatorio via Docker)**
Avvio solo tramite Docker:
```
docker compose -f docker-compose.yml up --build -d
```
Per fermare:
```
docker compose -f docker-compose.yml down
```
Script alternativo:
```
docker-run-dev.bat
```

**Docker**
- `docker-compose.yml` avvia:
  - `qsmith` (API FastAPI) su `:9082` con debugpy (porta `5678`)
  - `qsmith-ui` (Streamlit) su `:8501`
La UI usa `QSMITH_API_BASE_URL` (default in compose: `http://qsmith:9082`).

**ElasticMQ (SQS locale)**
- `elasticmq/docker-compose.yml`
- Console web: `http://localhost:9325`

**API e Strumenti**
- Swagger: `http://localhost:9082/docs`
- OpenAPI: `http://localhost:9082/openapi.json`
- UI Web (Streamlit): `http://localhost:8501`

**Test**
- `pytest app/test`
- Richiede Docker (Testcontainers avvia PostgreSQL)
