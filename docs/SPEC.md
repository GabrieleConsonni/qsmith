# Qsmith - Functional Specification

## 1. Project Overview
Qsmith e un'applicazione per gestire broker SQS, queue e payload JSON, con funzioni di test, invio/ricezione/ack messaggi e orchestrazione scenari.

L'applicazione e composta da:
- Backend FastAPI (`app/main.py`)
- UI Streamlit multipage (`app/ui/Qsmith.py`)

## 2. Scope Funzionale
La soluzione copre:
- configurazione broker SQS (ElasticMQ/Amazon)
- configurazione connessioni database (Postgres/Oracle/MSSQL)
- configurazione mock server API/queue con trigger asincroni
- gestione queue per broker
- operazioni runtime su queue (test connessione, send, receive, ack)
- gestione datasource 
    - JSON array
    - dataset (table/view da database)
- gestione scenari di test
    - creazione di scenari composti da step e operazioni
    - esecuzione singola o multipla di scenari
    - esecuzione singola di scenari in modalità debug  
- visualizzazione log applicativi 

## 3. Routing UI
Pagine disponibili:
- `Configurations` 
    - `Brokers`
    - `Database Connections`
    - `Mock Servers`
- `SQS Brokers` 
    - `Queues`
        - `Queue details`
- `Datasources`
    - `Json Array`
    - `Dataset`
- `Test scenarios`
    - `Scenarios`
        - `Scenario Editor` 
- `Logs`
- `Tools`


## 4. Specifiche per Pagina

### 4.1 Brokers
Obiettivi:
- visualizzare elenco broker configurati
- consentire inserimento/modifica/cancellazione broker
- aprire la pagina `Queues` del broker selezionato

Dati principali mostrati:
- code
- description
- tipo connessione/configurazione

### 4.2 Database Connections
Obiettivi:
- elenco connessioni database
- CRUD connessioni (Postgres/Oracle/MSSQL)
- test connessione configurata

### 4.3 Queues
Obiettivi:
- mostrare le queue del broker selezionato
- visualizzare metriche queue (messaggi, ultimo aggiornamento)
- aggiungere/modificare/cancellare queue
- navigare al `Queue details` della singola queue

### 4.4 Queue details
Header:
- metrica `Approximante number of messages`
- metrica `Not visible messages`
- azioni `Refresh` e `Test connection`

Tab disponibili:
- `Send`
- `Receive`

Funzioni `Send`:
- create/edit json-array body (dialog `Write json-array`)
- select datasource da JSON array salvati
- save json-array nel datasource
- send messages alla queue
- view results invio

Funzioni `Receive`:
- ricezione messaggi dalla queue
- preview JSON messaggi ricevuti
- ack messages (PUT su endpoint queue messages)
- extract json-array da messaggi ricevuti e salvataggio datasource
- clean preview

### 4.5 Json Array
Obiettivi:
- elenco datasource JSON array
- aggiunta/modifica/cancellazione item
- preview payload JSON

### 4.6 Dataset
Obiettivi:
- elenco dataset tabellari
- CRUD datasource database
- scelta tabella/view da connessione tramite dialog con tree tables/views
- preview dati tabella/view configurata

### 4.7 Test Scenarios
Obiettivi:
- selezionare scenario
- aggiunta/cancellazione item
- eseguire scenario selezionato
- navigare al `Scenario Editor` del singolo scenario


### 4.8 Scenario Editor
Obiettivi:
- Aggiungere step e operazioni allo scenario
- Eseguire step singolarmente o in gruppi
- Visualizzare stato ultima esecuzione di step/operazioni (check/error/idle)
- Mostrare avanzamento esecuzione scenario in tempo reale (step eseguiti / totali)
- I dialog `Add step` e `Add operation` supportano:
  - `Save and add`: salva in anagrafica (`steps`/`operations`) e aggiunge snapshot nello scenario
  - `Add only`: aggiunge solo snapshot nello scenario senza salvare nell'anagrafica
  - pannello sinistro con `Add` e `Delete` (delete dall'anagrafica)

Modello dati scenario:
- `scenario_steps` e `step_operations` contengono i dettagli funzionali (code/type/configuration_json) usati in esecuzione.
- Lo scenario non dipende più da `step_id`/`operation_id` in runtime.


### 4.9 Logs
Obiettivi:
- visualizzare i log
- filtrare log per livello, tipo, subject, messaggio e intervallo data
- pulire log vecchi per numero giorni

### 4.10 Mock Servers
Obiettivi:
- creare/modificare/cancellare mock server con endpoint dedicato
- configurare API mock (`method`, `path`, params/headers/body, response)
- configurare queue binding verso queue esistenti
- associare operazioni a trigger API e queue (incluso `run-scenario`)
- attivare/disattivare runtime mock server

Comportamento runtime:
- route runtime sotto prefisso fisso `/mock/{server_endpoint}/...`
- risposta API mock immediata, operazioni eseguite in background
- listener queue avviati solo quando il server e attivo
- su trigger queue viene eseguito `ACK` sempre (anche in caso errore operazioni)

## 5. API Funzionali Principali
- `/broker/connection` CRUD broker connection
- `/broker/{broker_id}/queue` CRUD queue e operazioni queue/messages
- `/data-source/json-array` CRUD JSON array datasource
- `/data-source/database` CRUD datasource database
- `/database/connection` CRUD connessioni database + test + metadata objects/preview
- `/elaborations/scenario` elenco/gestione scenari ed esecuzione
- `/elaborations/scenario/{scenario_id}/step/{scenario_step_id}/execute` esecuzione asincrona del singolo scenario-step
- `/elaborations/execution/{execution_id}/events` stream SSE eventi runtime esecuzione
- `/mock-server` CRUD configurazione mock server + activate/deactivate
- `/mock/{server_endpoint}/{path}` runtime mock API dispatcher
- `/logs/` elenco log
- `/logs/{days}` pulizia log

## 6. Vincoli Operativi
- Avvio standard via Docker Compose.
- UI dipende da `QSMITH_API_BASE_URL`.
- I test backend usano Docker/Testcontainers.
