# Qsmith - Istruzioni Operative per Codex

Leggi prima `docs/CODEX_CONTEXT.md` per contesto e comandi principali.

## Regole di lavoro generali
- Evita di inserire segreti o credenziali reali nei file del repo.
- Per ricerche nel repo preferisci `rg` (ripgrep).
- Quando identifichi una modifica strutturale, aggiorna questo file e la documentazione correlata.
- Per scenari: `scenario_steps`/`step_operations` sono snapshot funzionali (`code/type/configuration_json`), non riferimenti runtime a `steps`/`operations`.
- Prima di iniziare una modifica, leggi `docs/SPEC.md`, `docs/STORIES_INDEX.md` (se presente) e `docs/stories/*.md` rilevanti.
- Se una modifica impatta specifiche o piano di lavoro, aggiorna `docs/SPEC.md` e/o `docs/stories/QSM-*.md` e/o `README.md` e/o `docs/CODEX_CONTEXT.md`.
- Per bug fixing, consultare/aggiornare `docs/bugs/QSMB-*.md`.

## UI Streamlit - Hard Gate
Questa sezione e vincolante per ticket UI e code review.

### 1) Pattern architetturale obbligatorio
Usare sempre il pattern:
`Page -> Container -> Service -> StateKeys`

Regole per layer:
- `pages/`: orchestrazione view-level e routing, niente logica business e niente HTTP diretto.
- `components/`: rendering UI, validazioni leggere, composizione dialog/container.
- `services/`: accesso API e trasformazioni dati, senza side effects UI.
- `state_keys.py`: tutte le chiavi `session_state` del modulo.

### 2) Regole bloccanti (PASS/FAIL)
- Vietato fare chiamate HTTP dirette (`api_get/api_post/api_put/api_delete/requests.*`) nei file `pages/*`.
- Vietato usare in `services/*`: `st.error`, `st.warning`, `st.success`, `st.rerun`, `st.switch_page`, `st.stop`.
- Vietato introdurre nuove chiavi `session_state` come stringhe raw sparse: usare costanti in `state_keys.py`.
- Operazioni mutative devono avere submit esplicito (`st.form_submit_button` o bottone di conferma in `st.dialog`).
- Letture idempotenti ripetute devono valutare caching (`st.cache_data`/`st.cache_resource`) con invalidazione esplicita.

### 3) Regole di modularita e dimensione file
- Per file nuovi UI:
  - >350 linee: warning, motivare nel PR.
  - >500 linee: blocco, obbligo split.
- Per file legacy toccati >500 linee: obbligo split incrementale nel ticket o piano di split esplicito nel PR.
- Nelle feature UI creare/riusare package dedicati in `app/ui/<feature>/`.

### 4) Naming convention
Per nuovo codice UI usare:
- `*_container.py` per container/render principali.
- `*_dialog.py` per dialog.
- `*_service.py` per servizi.
- `state_keys.py` per stato.
- `models.py` per tipi/dto/view model (quando utili).

Nota compatibilita: in moduli esistenti sono ammessi nomi storici (`dialogs.py`, `*_component.py`) ma nuove aggiunte devono convergere allo standard.

### 5) Error handling UI
- I service restituiscono dati o errori tipizzati (es. risultato + messaggio), non emettono toast/error UI direttamente.
- La UI mappa gli errori in messaggi user-safe.
- Dettagli tecnici restano nei log applicativi, non in messaggi utente verbose.

### 6) Testing minimo per ticket UI
Ogni ticket UI deve includere:
- test unitari su transformer/validator/service introdotti o modificati;
- checklist manuale di regressione UI (navigazione, CRUD, feedback errori, stato).

Assenza totale di test o checklist e motivo di blocco PR salvo eccezioni motivate.

## Definition of Done UI (obbligatoria)
Ogni PR/ticket UI deve dichiarare `PASS/FAIL` per:
- Pattern `Page -> Container -> Service -> StateKeys` rispettato.
- Nessuna chiamata HTTP diretta nei `pages/*` nuovi/modificati.
- Nessun side effect UI nei `services/*` nuovi/modificati.
- Nuove chiavi stato registrate in `state_keys.py`.
- Submit esplicito per mutazioni (`form` o dialog confermato).
- Caching valutato e documentato per fetch idempotenti.
- Soglie dimensione file rispettate o piano di split allegato.
- Test unitari e checklist manuale allegati.

## Legacy modernization policy
Policy default: `touched-files only`.

- Hard-gate su file nuovi e file toccati nel ticket corrente.
- Nessun blocco automatico su file legacy non toccati.
- Se il ticket tocca file monolitici legacy, includere almeno una riduzione incrementale della complessita oppure un piano tecnico con priorita e cutoff.

## UI code review rubric (sanatoria esistente)
Usare severita `High / Medium / Low`.

### High (bloccante)
- Violazione hard-gate (HTTP in page, side effects UI nei service, assenza submit mutazioni).
- Regressioni funzionali o stato incoerente cross-page.
- Nuovo file >500 linee senza split.

### Medium
- Mancata centralizzazione state keys.
- Error handling incoerente o messaggi utente non adeguati.
- Caching mancante in flussi chiaramente idempotenti e costosi.

### Low
- Naming non allineato allo standard.
- Dupliche minori, refactor cosmetici, miglioramenti leggibilita.

Template review consigliato (per ogni finding):
- Severita:
- File:
- Evidenza:
- Impatto:
- Fix proposto:

## Priorita code review UI (fase successiva)
Ambito iniziale:
- `app/ui/scenarios/components/scenarios_component.py`
- `app/ui/steps/step_component.py`
- `app/ui/scenarios/components/scenario_operation_component.py`
- `app/ui/mock_servers/components/mock_server_editor_component.py`
- `app/ui/queues/components/queue_details_component.py`
- `app/ui/pages/Logs.py`

Output atteso:
- findings ordinati per severita con evidenza file;
- azioni di sanatoria incrementali;
- priorita di refactor per ridurre monoliti e side-effect cross-layer.

## Esecuzione e test
- Avvio obbligatorio via Docker:
```bash
docker compose -f docker-compose.yml up --build -d
```
- UI Streamlit via Docker: stesso `docker-compose.yml` (porta `8501`), base URL `QSMITH_API_BASE_URL`.
- Test backend:
```bash
pytest test
```
I test usano Docker (Testcontainers per PostgreSQL).

## Punti di ingresso
- API principale: `app/main.py`
- UI Streamlit: `app/ui/Qsmith.py`
- Migrazioni: `alembic/`
