# Qsmith
Qsmith e un queue manager con backend FastAPI e UI Streamlit.

## Prerequisiti
- Docker Desktop
- Python 3.13 (solo se vuoi eseguire tool/test fuori dai container)
- ElasticMQ

## ElasticMQ locale (opzionale)
Per avviare solo ElasticMQ in locale:
```bash
cd elasticmq
docker compose up -d
```

- SQS endpoint: `http://localhost:9324`
- Console web: `http://localhost:9325`

## Avvio (docker-compose)
Avvio stack API + UI:
```bash
docker compose -f docker-compose.yml up --build -d
```

Stop stack:
```bash
docker compose -f docker-compose.yml down
```

Script alternativo Windows:
```bat
docker-run-dev.bat
```

## Repository Map
- `app/`: backend FastAPI e codice UI Streamlit
- `app/main.py`: entrypoint API
- `app/ui/Qsmith.py`: entrypoint UI Streamlit
- `alembic/`: migrazioni database
- `docker/`: Dockerfile API/UI
- `elasticmq/`: compose e configurazione ElasticMQ locale
- `docs/`: documentazione funzionale e operativa

## Endpoint utili
- UI Streamlit: `http://localhost:8501`
- API FastAPI: `http://localhost:9082`
- Swagger: `http://localhost:9082/docs`
- OpenAPI JSON: `http://localhost:9082/openapi.json`
- Debugpy: `localhost:5678` (container `qsmith`)

## Tema Streamlit
La configurazione tema viene letta da `.streamlit/config.toml` nella directory da cui esegui `streamlit run`.

In questo progetto la UI parte da `app/ui`, quindi in Docker la cartella `.streamlit` del repo viene montata anche in `app/ui/.streamlit` per rendere il tema effettivo.

Se avvii la UI in locale, usa uno di questi approcci:
- esegui `streamlit run app/ui/Qsmith.py` dalla root del repo;
- oppure mantieni anche `app/ui/.streamlit/config.toml` allineato al file in root.

### Installazione in locale

## Environment Python
```bash
python -m venv .venv
```
```bash
.\.venv\Scripts\Activate.ps1
```

## Dipendenze
Installazione dipendenze ambiente Python locale:
```bash
pip install -r requirements.txt
```

Rigenerazione `docker-requirements.txt` da `requirements.in`:
```bash
docker compose -f docker-compose-compile-requirements.yml run --rm compiler
```

## Test
```bash
pytest test
```

Nota: i test usano Testcontainers (Docker richiesto).

## Alembic
Esempi comandi:
```bash
alembic revision --autogenerate -m "YYYYMMDDHH_desc"
alembic upgrade head
alembic downgrade -1
alembic current
alembic history
alembic heads
alembic branches
alembic show <revision>
```


