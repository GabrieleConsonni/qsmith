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
- gestione queue per broker
- operazioni runtime su queue (test connessione, send, receive, ack)
- gestione datasource JSON array
- gestione datasource database (table/view)
- visualizzazione log applicativi
- gestione scenari di elaborazione (esecuzione scenario)

Non copre (stato attuale):
- Home page dedicata con quick actions
- Tools operativi completi (pagina placeholder)

## 3. Routing UI
Pagine disponibili:
- `Brokers`
- `Database Connections`
- `Queues`
- `Queue details`
- `Json Array`
- `Database Datasources`
- `Scenarios`
- `Logs`
- `Tools`

La navigazione avviene via sidebar; la selezione broker impatta il contesto di `Queues` e `Queue details`.

## 4. Specifiche per Pagina

### 4.1 Brokers
Obiettivi:
- visualizzare elenco broker configurati
- consentire inserimento/modifica/cancellazione broker
- aprire contesto queue del broker selezionato

Dati principali mostrati:
- code
- description
- tipo connessione/configurazione

### 4.2 Queues
Obiettivi:
- mostrare le queue del broker selezionato
- visualizzare metriche queue (messaggi, ultimo aggiornamento)
- aggiungere/modificare/cancellare queue
- navigare al dettaglio della singola queue

### 4.3 Queue details
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

### 4.4 Json Array
Obiettivi:
- elenco datasource JSON array
- aggiunta/modifica/cancellazione item
- preview payload JSON

### 4.5 Scenarios
Obiettivi:
- ricaricare elenco scenari da backend
- selezionare scenario
- eseguire scenario selezionato

### 4.6 Logs
Obiettivi:
- ricaricare log
- filtrare log per livello, tipo, subject, messaggio e intervallo data
- pulire log vecchi per numero giorni

### 4.7 Tools
Stato attuale:
- pagina placeholder "Utility operative in arrivo."

### 4.8 Database Connections
Obiettivi:
- elenco connessioni database
- CRUD connessioni (Postgres/Oracle/MSSQL)
- test connessione configurata

### 4.9 Database Datasources
Obiettivi:
- elenco datasource tabellari
- CRUD datasource database
- scelta tabella/view da connessione tramite dialog con tree tables/views
- preview dati tabella/view configurata

## 5. API Funzionali Principali
- `/broker/connection` CRUD broker connection
- `/broker/{broker_id}/queue` CRUD queue e operazioni queue/messages
- `/data-source/json-array` CRUD JSON array datasource
- `/data-source/database` CRUD datasource database
- `/database/connection` CRUD connessioni database + test + metadata objects/preview
- `/elaborations/scenario` elenco/gestione scenari ed esecuzione
- `/logs/` elenco log
- `/logs/{days}` pulizia log

## 6. Vincoli Operativi
- Avvio standard via Docker Compose.
- UI dipende da `QSMITH_API_BASE_URL`.
- I test backend usano Docker/Testcontainers.
