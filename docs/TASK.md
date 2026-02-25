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
- [x] In fase di aggiunta di uno step aprire dialog:
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
- [x] Nella crud degli scenari, in fase di aggiunta di un'operazione ad uno step aprire dialog:
    - mettere selectbox con scelta operazioni esistenti
    - + per eventuale nuova operazione
    - in caso di scelta di operazione esistente:
        - mostrare i dati dell'operazione in sola lettura 
        - abilitare bottone con `add` 
    - in caso di scelta nuova operazione 
        - abilitare i campi per l'inserimento ( seguire ConfigurationOperationDto)
        - abilitare bottone `save and add`  

---

## QSM-020 - Gestione database connections
- [x] Aggiungere una pagina sotto Configurations per la gestione delle connessioni a db
- [x] la crud è uguale a quella dei brokers eccezion fatta per `open queues`
- [x] Al momento gestiamo solo connessioni Postgres, aggiungi Oracle e MSSQL

---

## QSM-020 - Gestione database datasources
- [x] Aggiungere una pagina sotto datasources per la gestione dei sorgenti di tipo db (tabelle)
- [x] la crud è uguale a quella fatta per Json array eccezzion fatta per la parte sinistra in cui vediamo la preview della tabella configurata
- [x] quando aggiungiamo una tabella si apre un dialog in cui:
 - si sceglie code e descrizione
 - si sceglie la connessione
 - viene mostrato un tree in cui ci sono tabelle e views
 - scelta la tabella\view si clicca `add` e viene creato il db datasource

---

## QSM-021 - Logs
- [x] Pagina logs
- [x] Ricarica elenco logs
- [x] Filtri lato UI (livello, tipo, subject, messaggio, data)
- [x] Pulizia log vecchi (`DELETE /logs/{days}`)

---

## QSM-022 - Modifiche ScenarioEditor
- [v] Sostituire il bottone `+ Add Scenario Step` con : 
    - [v] `+ Add new step` -> apre dialog con code, description, stepType etc..
    - [v] `iconaImport Import step` -> apre dialog con selectbox e preview dei dati dello step selezionato

---

## QSM-023 - Modifiche editor step 
- [x] Se nel dialog di aggiunta step l'utente sceglie come stepType `DATA_FROM_JSON_ARRAY` allora viene mostrata selectbox su json array configurati
    - [x] scelto il json appare preview del json
    - [x] la select box mostra solo le descrizioni 
- [x] Se nel dialog di aggiunta step l'utente sceglie come stepType `DATA` allora viene mostrata una textbox per scrivere un json e pulsante beautify per formattare il testo
- [x] Se nel dialog di aggiunta step l'utente sceglie come stepType `DATA_FROM_DB` allora viene mostrata una selectbox su dataset configurati
    - [x] la selectbox contiene solo le descrizioni
    - [x] togliere connection id e table name
    - [x] togliere la query e order by
    - [x] togliere i parametri anche da DataFromDbConfigurationStepDto (gestiremo poi l'elaborazione)
- [x] Se nel dialog di aggiunta step l'utente sceglie come stepType `DATA_FROM_QUEUE` allora viene mostrata una selectbox su brokers configurati. Scelto il broker si attiva seconda selectbox su queue del broker
    - [x] le selectbox contengono solo le descrizioni

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
