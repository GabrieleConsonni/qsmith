# Qsmith - Istruzioni Operative per Codex

Leggi prima `docs/CODEX_CONTEXT.md` per contesto e comandi principali.

**Regole di Lavoro**
- Evita di inserire segreti o credenziali reali nei file del repo.
- Se tocchi i modelli SQLAlchemy in `app/_alembic/models`, aggiorna le migrazioni in `alembic/`.
- Per ricerche nel repo preferisci `rg` (ripgrep).
- Mantieni la logica di fetch API concentrata nei service per facilitare test e riuso.
- In UI, se possibile estrai componenti in file separati e organizzali per package (esempio: `brokers/components`) e chiamali con `..._component.py` .
- Le chiamate API per le queue devono stare in servizi dedicati (`queues.services.queue_service`).
- Quando identifichi una modifica strutturale, aggiorna sempre questo file e i documenti correlati.
- Prima di iniziare una modifica, leggi `docs/SPEC.md` (analisi funzionale) e `docs/TASK.md` (piano di lavoro).
- Se una modifica impatta specifiche o piano di lavoro, aggiorna `docs/SPEC.md` e/o `docs/TASK.md` e/o `README.md` e/o `docs/CODEX_CONTEXT.md`.
- Per la risoluzione di bug consultare e aggiornare il file `docs/BUGS.md` essi hanno sintassi QSMB-XXX

**Esecuzione e Test**
- Avvio obbligatorio via Docker:
```
docker compose -f docker-compose.yml up --build -d
```
- UI Streamlit via Docker: usa lo stesso `docker-compose.yml` (porta `8501`)
  - Base URL configurata con `QSMITH_API_BASE_URL`
- Test:
```
pytest app/test
```
I test usano Docker (Testcontainers per PostgreSQL).

**Punti di Ingresso**
- API principale: `app/main.py`
- UI Streamlit: `app/ui/Qsmith.py`
- Migrazioni: `alembic/`
