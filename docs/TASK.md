# Qsmith - Task Breakdown

## Stato generale
- [x] Baseline UI multipage Streamlit configurata
- [x] Baseline API FastAPI configurata
- [x] Avvio stack via `docker-compose.yml`

---

## QSM-008 - Brokers & Queues
- [x] Caricamento brokers all'avvio UI
- [x] Visualizzazione queue per broker selezionato
- [x] Metriche queue (messages sent/received + last update)
- [x] Refresh lista queue
- [x] CRUD broker connection
- [x] CRUD queue
- [x] Navigazione a `Queue details`

---

## QSM-009 - Queue details
- [x] Pagina dedicata gestione singola queue
- [x] Context sync (`broker_id`, `queue_id`) via stato/query params
- [x] Header con metriche queue + azioni refresh/test
- [x] Tab `Send`
- [x] Tab `Receive`

---

## QSM-011 - Queue Send
- [x] Layout 3 colonne (azioni / preview / send)
- [x] Dialog `Write json-array` (body, beautify, conferma)
- [x] Dialog `Select datasource` con preview payload
- [x] Dialog `Save json-array` in datasource
- [x] Invio messaggi a queue
- [x] Dialog risultati invio

---

## QSM-012 - Queue Receive
- [x] Ricezione messaggi
- [x] Preview JSON messaggi ricevuti
- [x] Ack messaggi ricevuti (`PUT /broker/{broker_id}/queue/{queue_id}/messages`)
- [x] Extract json-array da messaggi ricevuti
- [x] Salvataggio extracted json-array in datasource
- [x] Pulizia preview

---

## QSM-016 - Json array datasources
- [x] Pagina elenco json-array
- [x] CRUD json-array
- [x] Integrazione json-array con flussi queue send/receive

---

## QSM-017 - CRUD Scenarios
- [x] Modificare la pagina scenarios
    - prendere ad esempio la maschera dei json array
    - a sinistra l'elenco degli scenari esistenti
    - a destra l'edit\creazione degli scenari
    - nella destra elenco degli scenario_step con expander con bottoni aggiungi in basso, delete e modifica per ogni container
    - dentro ogni expander step elenco delle step_operation con bottoni aggiungi in basso, delete e modifica per ogni container

---

## QSM-018 - Gestione Scenario_steps
- [x] Nella crud degli scenari, per ogni container di scenario sulla sinistra, mettere bottone esegui
- [ ] In fase di aggiunta di uno step aprire dialog:
    - mettere selectbox con scelta steps esistenti
    - + per eventuale nuovo step
    - in caso di scelta di step esistente:
        - mostrare i dati dello step in sola lettura 
        - abilitare bottone con `add` 
    - in caso di scelta nuovo step 
        - abilitare i campi per l'inserimento (seguire ConfigurationStepDto)
        - abilitare bottone `save and add`
    - al salvataggio renderizzare nuovo step

---

## QSM-019 - Gestione  Step_operations 
- [ ] Nella crud degli scenari, in fase di aggiunta di un'operazione ad uno step aprire dialog:
    - mettere selectbox con scelta operazioni esistenti
    - + per eventuale nuova operazione
    - in caso di scelta di operazione esistente:
        - mostrare i dati dell'operazione in sola lettura 
        - abilitare bottone con `add` 
    - in caso di scelta nuova operazione 
        - abilitare i campi per l'inserimento ( seguire ConfigurationOperationDto)
        - abilitare bottone `save and add`  

---

## QSM-021 - Logs
- [x] Pagina logs
- [x] Ricarica elenco logs
- [x] Filtri lato UI (livello, tipo, subject, messaggio, data)
- [x] Pulizia log vecchi (`DELETE /logs/{days}`)

---

## QSM-030 - Home & Quick Actions
- [ ] Home page dedicata
- [ ] Quick action: crea scenario
- [ ] Quick action: aggiungi sorgente dati
- [ ] Quick action: aggiungi broker

---

## QSM-040 - Tools
- [x] Pagina `Tools` placeholder
- [ ] Utility operative reali da definire

---

## QSM-050 - Documentazione
- [x] Riallineamento `README.md` alla codebase
- [x] Riallineamento `AGENT.md` ai path reali
- [x] Riallineamento `docs/CODEX_CONTEXT.md`
- [x] Aggiornamento `docs/SPEC.md`
- [x] Stesura documentazione funzionale su Confluence
