# Qsmith - Istruzioni Operative per Codex

Leggi prima `docs/CODEX_CONTEXT.md` per contesto e comandi principali.

**Regole di Lavoro**
- Evita di inserire segreti o credenziali reali nei file del repo.
- Per ricerche nel repo preferisci `rg` (ripgrep).
- Quando identifichi una modifica strutturale, aggiorna sempre questo file e i documenti correlati.
- Per scenari: `scenario_steps`/`step_operations` sono snapshot funzionali (code/type/configuration_json), non riferimenti runtime a `steps`/`operations`.
- Prima di iniziare una modifica, leggi `docs/SPEC.md` (analisi funzionale) e `docs/TASK.md` (piano di lavoro).
- Se una modifica impatta specifiche o piano di lavoro, aggiorna `docs/SPEC.md` e/o `docs/TASK.md` e/o `README.md` e/o `docs/CODEX_CONTEXT.md`.
- Per la risoluzione di bug consultare e aggiornare il file `docs/BUGS.md` essi hanno sintassi QSMB-XXX
- Per modifiche\aggiunte alla UI (Streamlit) non scrivere tutto in un unico file ma partendo dalla pagina:
  - Dove possibile rendila modulare estraendo i componenti in packages (esempio: `ui/brokers`)
  - Dentro i packages metti sottocartelle services, components e models. 
  - Mantieni la logica di fetch API concentrata nei service per facilitare test e riuso.
  - Per i componenti grafici chiamali con il loro tipo ad esempio:
    - se sono container `..._container.py`
    - se sono dialog `..._dialog.py`

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
