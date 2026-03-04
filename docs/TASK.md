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
- [x] la crud Ã¨ uguale a quella dei brokers eccezion fatta per `open queues`
- [x] Al momento gestiamo solo connessioni Postgres, aggiungi Oracle e MSSQL

---

## QSM-020 - Gestione database datasources
- [x] Aggiungere una pagina sotto datasources per la gestione dei sorgenti di tipo db (tabelle)
- [x] la crud Ã¨ uguale a quella fatta per Json array eccezzion fatta per la parte sinistra in cui vediamo la preview della tabella configurata
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
    - [v] `iconaImport Import step` -> apre dialog con selectbox e preview dei dati dello step selezionato

---

## QSM-023 - Modifiche ScenarioEditor - editor steps 
- [v] Se nel dialog di aggiunta step l'utente sceglie come stepType `DATA_FROM_JSON_ARRAY` allora viene mostrata selectbox su json array configurati
    - [v] scelto il json appare preview del json
    - [v] la select box mostra solo le descrizioni 
- [v] Se nel dialog di aggiunta step l'utente sceglie come stepType `DATA` allora viene mostrata una textbox per scrivere un json e pulsante beautify per formattare il testo
- [v] Se nel dialog di aggiunta step l'utente sceglie come stepType `DATA_FROM_DB` allora viene mostrata una selectbox su dataset configurati
    - [v] la selectbox contiene solo le descrizioni
    - [v] togliere connection id e table name
    - [v] togliere la query e order by
    - [v] togliere i parametri anche da DataFromDbConfigurationStepDto (gestiremo poi l'elaborazione)
- [v] Se nel dialog di aggiunta step l'utente sceglie come stepType `DATA_FROM_QUEUE` allora viene mostrata una selectbox su brokers configurati. Scelto il broker si attiva seconda selectbox su queue del broker
    - [v] le selectbox contengono solo le descrizioni

---

## QSM-024 - Modifiche ScenarioEditor - editor operations
- [v] Nel container dello step sostituire il bottone `+ Add operation` con : 
    - [v] `+ Add new operation` -> apre dialog con code, description, operationType etc..
    - [v] `iconaImport Import operation` -> apre dialog con selectbox e preview dei dati dell'operation selezionato
- [v] Se nel dialog di aggiunta operation l'utente sceglie come operationType `PUBLISH` allora viene mostrata una selectbox su brokers configurati. 
      Scelto il broker si attiva seconda selectbox su queue del broker la parte template_id e template_params lo svilupperemo in un secondo momento.
- [v] Se nel dialog di aggiunta operation l'utente sceglie come operationType `SAVE_INTERNAL_DB` allora viene mostrata una textbox per il nome tabella.
- [v] Se nel dialog di aggiunta operation l'utente sceglie come operationType `SAVE_EXTERNAL_DB` allora viene mostrata una selectbox su dataset configurati

## QSM-025 - Fix step e operazioni
- [v] identificare criticitÃ  nelle operazioni e coprire le funzionalitÃ  con test di unitÃ 
- [v] identificare criticitÃ  negli step e coprire le funzionalitÃ  con test di unitÃ 

## QSM-026 - Esecuzione step scenario
- [x] creare architettura SSE (Server-Sent Events) fra Qsmith e Qsmith UI in modo tale che il BE possa inviare eventi al FE per aggiornarlo 
- [x] aggiungere bottone check\errore\pallino vuoto a fianco della label steptype (servirÃ  per capire se l'ultima esecuzione dello step Ã¨ andata a buon fine)
- [x] aggiungere bottone check\errore\pallino vuoto a fianco della descrizione dell'oprazione (servirÃ  per capire se l'ultima esecuzione dell'operazione Ã¨ andata a buon fine)
- [x] aggiungere pulsante per esecuzione singolo step alla maschera dello scenarioEditor nel container dello step a finaco ai bottoni add\import operation
- [x] alla pressione del botton di avvio mostrare dialog che richiede se eseguire anche i precedenti o solo il singolo ( in inglese )
- [x] aggiungere api per esecuzione di step scenario ( asincrona ) con aggiornamenti al FE
- [x] all'esecuzione dello step viene inviato l'esito (log) al FE
- [x] all'esecuzione dell'operazione viene inviato l'esito (log) al FE
- [x] in basso a destra un elemento che indichi "Test scenario running: 3/6 step executed"

---

## QSM-027 - Snapshot scenario_step / step_operation
- [x] `scenario_steps` e `step_operations` aggiornati a modello snapshot (code/type/configuration_json)
- [x] dialog add step/operation: aggiunto `Add only`
- [x] dialog add step/operation lato sinistro: aggiunto `Delete` sotto `Add`
- [x] Scenario Editor renderizza dettagli da `scenario_steps` / `step_operations`
- [x] Runtime esecuzione step/operation basato su snapshot scenario (senza lookup da anagrafica)

## QSM-028 - Scenario executions
- Ã¨ necessario persistere a db le esecuzioni degli scenari e vederli sia in scenario editor che in home page
- l'esecuzione mostra righe di testata con il nome dello scenario e l'esito globale e il datetime
- la riga di testata Ã¨ ampliabile con il dettaglio degli step con esito e datetime
- gli step contengono le operazioni con esito e datetime
- [x] creare la struttura a db `scenario_executions`, `scenario_step_executions`, `step_operation_executions`
- [x] modificare l'elaborazione degli scenari\step\operatzioni in modo che registrino le esecuzioni
- [x] Aggiungere una home page
    - [x] Aggiungere sezione `Test scenario executions` in cui mettere solo gli scenari exectution e bottone che naviga allo scenarioEditor relativo
- [x] Modifiche alla scenario editor
    - [x] Dividere lo sceario editor in due parti: la parte di sinistra con gli scenari executions, la parte di destra come adesso.
    - [x] Gli scenari hanno ordine dal piÃ¹ recente al piÃ¹ vecchio
    - [x] Aggiungere `bottone di cancellazione` e `bottone icona cerca`
    - [x] Alla selezione del `bottone cerca`, gli indicatori dello scenario: step, operation si aggiornano con i risultati dell'esecuzione. 
    - [x] in basso ad ogni step\operazione mettere (eventualmenten) il messaggio di errore come feedback.
    - [x] quando viene lanciato uno scenario\step\step gli indicatori e i messaggi di feedback si svuotano\puliscono  


## QSM-029 -Modifiche alla pagina degli scenari 
- [x] raggruppare i due bottoni modifica e delete dentro uno unico che apre dialog con possibilità di cancellare scenario e modificare la descrizione
- [x] togliere pulsante di avvio esecuzione scenario
- [x] all'aggiunta di un nuovo scenario mostrare dialog per modifica code e descrizione. al salvataggio apre lo scenario editor


## QSM-030 - JsonArray Assert operations 
- [x] aggiungere una nuova operation di tipo assert. Essa ha due field generali.
    - Error message
    - evaluetedObjectType: `Json\Data`, `Table`, etc ... (ampliabile)
- [x] per il tipo `Json\Data` Ã¨ possibile configurare:
    - [x] `NotEmpty` <-- verifica che i dati non siano vuoti
    - [x] `Empty` <-- verifica che i dati siano vuoti
    - [x] `SchemaValidation` <-- verifica che i dati in formato json rispettino uno schema
        - impostare lo schema per la verifica
    - [x] `Contains` <-- verifica che i dati siano contenuti nel json array impostato
        - impostare il json array expected
        - impostare un array di keys per fare il confronto
    - [x] `JsonArrayEquals` <-- verifica che i dati siano uguali al json array impostato
        - impostare il json array expected
- [x] introdurre una family `assert` con un evalutor orchestratore\composite + strategy interne simile a quanto fatto per step_executor (NotEmptyData, EmptyData, ecc.).
- [x] modificare il dialog delle operazioni per integrare questa funzionalitÃ 
- [x] integrare i test esistenti


## QSM-031 - Table Assert Operations (prima parte)
- [ ] Aggiungere all'evalutor degli assert anche il tipo Table
- [ ] per il tipo Table Ã¨ possibile configurare:
    - [ ] `Exists` <-- verifica che una tabella esista a db
        - impostare connessione e nome tabella
    - [ ] `Count` <-- verifica che una tabella abbia il numero di righe configurato
        - impostare connessione e nome tabella
        - impostare l'expectedCount 


## QSM-032 - Table Assert Operations (seconda parte)
- [ ] aggiungere all'evaluator degli assert table
    - [ ] `Contains` <-- verifica che i dati siano contenuti nella tabella
        - impostare connessione e nome tabella expected
        - impostare il mapping data keys con le colonne della tabella 
    - [ ] `TableEquals` <-- verifica che due tabelle abbiano lo stesso contenuto utilizzando le funzionalità native dei db.
        - impostare connessione 
        - nome tabella expected
        - nome tabella actual

## QSM-033 - Mock servers
- [ ] Aggiungere una pagina e relativa anagrafica per i mock server


## QSM- - Short Actions
- [ ] aggiungere una sezione in home, sopra i `Test scenario executions` 
- [ ] Mettere i seguenti bottoni:
     a. Configura connessione broker
     b. Configura connessione a db
     c. Aggiungi json array
     d. Aggiungi dataset
     e. Crea scenario di test 
- [ ] renderizzarli in questo modo
    [vuoto | e | a | b | vuoto]
    [vuoto | c | d | vuoto] 
    Test scenario Execution
    divider

