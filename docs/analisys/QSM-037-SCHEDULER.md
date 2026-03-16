Sì, riesco già a stendere un’analisi e un plan senza altro. Ho abbastanza contesto per proporti una soluzione coerente con Qsmith, con esecuzioni asincrone di suite, stato attivo/disattivo, hook/test runtime e persistenza delle esecuzioni. In particolare, la spec già prevede l’esecuzione di suite e la gestione runtime/eventi, quindi la schedulazione si inserisce bene sopra questo modello, senza inventare un motore separato.  Inoltre il documento su context/commands conferma che `runSuite` è già un comando runtime e che il contesto di esecuzione è strutturato (`runEnvelope`, `global`, `local`, `result`), quindi la schedulazione può limitarsi a “decidere quando lanciare” una suite, lasciando invariato il motore di esecuzione. 

Ti lascio sotto un’analisi operativa già pronta per Codex.

---

# Qsmith – Analisi e plan schedulazione Test Suite

## 1. Obiettivo

Introdurre in Qsmith una funzionalità di **schedulazione delle test suite** che consenta di:

* associare una schedulazione a una test suite
* definire una **frequenza di esecuzione** (`minuti`, `ore`, `giorni`, ecc.)
* attivare/disattivare la schedulazione
* generare esecuzioni della suite usando il runtime già esistente
* mantenere tracciabilità di stato, prossima esecuzione e ultima esecuzione

La schedulazione deve essere un **trigger applicativo** che invoca l’esecuzione della suite già supportata dal sistema, non un secondo motore di test. Questo è coerente con l’architettura attuale, dove le suite sono già entità eseguibili e le esecuzioni sono persistite e osservabili tramite eventi runtime. 

---

## 2. Scelte architetturali

### 2.1 Concetto chiave

La schedulazione non esegue test “in proprio”, ma:

1. legge le schedulazioni attive
2. valuta se sono “due”
3. crea una normale esecuzione di test suite
4. aggiorna metadati scheduler

Quindi:

* **motore suite**: resta quello attuale
* **scheduler service**: nuovo componente applicativo
* **scheduler persistence**: nuova tabella o set di tabelle

### 2.2 Approccio consigliato

Per il tuo stack Python + container, la soluzione più semplice e robusta è:

* **scheduler loop interno al backend**
* polling periodico ogni X secondi
* lock anti-concorrenza
* creazione run asincrona della suite

Questo evita, almeno nella prima versione:

* dipendenze esterne tipo Celery/Redis
* cron di sistema nel container
* complessità distribuita

Per una V1 è la scelta più adatta.

---

## 3. Modello funzionale

## 3.1 Nuova entità: Test Suite Schedule

Campi minimi:

* `id`
* `test_suite_id`
* `active` boolean
* `frequency_type`
* `frequency_value`
* `start_at` opzionale
* `end_at` opzionale
* `timezone`
* `next_run_at`
* `last_run_at`
* `last_status`
* `created_at`
* `updated_at`

### 3.2 Frequenze supportate

Per partire ti consiglio di supportare due modalità:

### A. Interval

Schedulazione ogni N unità:

* ogni `N` minuti
* ogni `N` ore
* ogni `N` giorni

Campi:

* `frequency_mode = interval`
* `frequency_unit = minutes | hours | days`
* `frequency_value = int`

Esempi:

* ogni 5 minuti
* ogni 2 ore
* ogni 1 giorno

### B. Weekly semplice

Molto utile per test ricorrenti:

* giorni della settimana selezionabili
* orario fisso

Campi:

* `frequency_mode = weekly`
* `weekdays = [1..7]`
* `time_of_day = "HH:MM:SS"`

Esempi:

* lun/mer/ven alle 09:00
* tutti i giorni lavorativi alle 08:30

### Per la V1

Se vuoi essere rapido: implementa prima solo **interval**.
Se vuoi una feature subito più utile: **interval + weekly**.

---

## 4. Regole di business

## 4.1 Attivo/disattivo

* Se `active = false`, la schedulazione non produce nuove esecuzioni.
* La disattivazione non annulla run già partiti.

## 4.2 Una schedulazione = una suite

Ogni schedulazione punta a una sola `test_suite`.

Una suite può avere:

* una sola schedulazione attiva, oppure
* più schedulazioni diverse

Ti consiglio di consentire **più schedulazioni per la stessa suite**, perché apre casi utili:

* smoke ogni 15 minuti
* regression ogni giorno alle 23:00

## 4.3 Concorrenza

Serve una policy chiara se una suite è ancora in esecuzione quando scatta la successiva.

Opzioni:

* `skip_if_running`
* `queue_if_running`
* `allow_parallel`

Per Qsmith consiglierei default:

* **`skip_if_running`**

Perché è più sicuro e prevedibile in ambito test.

Campo consigliato:

* `overlap_policy = skip | queue | parallel`

V1: implementa solo `skip`.

## 4.4 Calcolo next_run_at

Ogni volta che:

* crei schedulazione
* modifichi schedulazione
* parte una run
* fallisce una run

ricalcoli `next_run_at`.

## 4.5 Errori di esecuzione

Se il lancio della suite fallisce:

* la schedulazione resta attiva
* salvi `last_status = error`
* ricalcoli comunque `next_run_at`

Così non si blocca tutto per un errore temporaneo.

---

## 5. Impatto sul runtime esistente

La spec già prevede:

* test suite eseguibili
* esecuzioni persistite
* eventi runtime/SSE 

Quindi lo scheduler deve solo creare una nuova esecuzione con metadati aggiuntivi nel `runEnvelope`, ad esempio:

```json
{
  "run_id": "uuid",
  "trigger": {
    "type": "schedule",
    "schedule_id": "uuid",
    "schedule_code": "nightly-regression"
  },
  "constants": {}
}
```

Questo è coerente con il modello di contesto esistente, dove il `runEnvelope` rappresenta l’origine del run e contiene costanti e metadati di lancio. 

Ti consiglio quindi di estendere il launch context con un trigger di tipo `schedule`.

---

## 6. Data model proposto

## 6.1 Tabella `test_suite_schedules`

Campi suggeriti:

* `id`
* `code` opzionale univoco leggibile
* `description`
* `test_suite_id` FK
* `active` boolean not null default true

### configurazione frequenza

* `frequency_mode` → `interval | weekly`
* `frequency_unit` → `minutes | hours | days` nullable
* `frequency_value` → int nullable
* `weekdays_json` → json nullable
* `time_of_day` → time nullable

### finestra validità

* `start_at` datetime nullable
* `end_at` datetime nullable
* `timezone` varchar default `Europe/Rome`

### controllo runtime

* `overlap_policy` → `skip`
* `next_run_at` datetime nullable
* `last_run_at` datetime nullable
* `last_status` → `idle | success | error | skipped`
* `last_execution_id` nullable
* `last_error_message` text nullable

### audit

* `created_at`
* `updated_at`

## 6.2 Tabella opzionale `test_suite_schedule_runs`

Utile se vuoi storico specifico dello scheduler, separato dalle execution normali.

Campi:

* `id`
* `schedule_id`
* `execution_id`
* `scheduled_at`
* `started_at`
* `finished_at`
* `status`
* `message`

Per la V1 puoi anche evitarla e usare solo:

* `last_*` sulla schedule
* tabella execution già esistente

---

## 7. API proposte

### CRUD schedulazioni

* `GET /elaborations/test-suite-schedules`
* `POST /elaborations/test-suite-schedules`
* `GET /elaborations/test-suite-schedules/{id}`
* `PUT /elaborations/test-suite-schedules/{id}`
* `DELETE /elaborations/test-suite-schedules/{id}`

### Azioni rapide

* `POST /elaborations/test-suite-schedules/{id}/activate`
* `POST /elaborations/test-suite-schedules/{id}/deactivate`
* `POST /elaborations/test-suite-schedules/{id}/run-now`

### Filtri utili

* per `test_suite_id`
* per `active`
* per `last_status`

---

## 8. UI proposta

Nel menu `Test Suites`, aggiungerei una nuova sezione:

* `Test Suites`
* `Schedules`

Oppure nel `Suite Editor`:

* tab `Schedule`

### Form schedulazione

Campi:

* test suite
* attivo/disattivo
* modalità: `interval | weekly`
* se interval:

  * valore
  * unità
* se weekly:

  * giorni settimana
  * orario
* timezone
* start_at opzionale
* end_at opzionale

### Lista schedulazioni

Colonne:

* suite
* frequenza
* attiva
* prossima esecuzione
* ultima esecuzione
* ultimo stato

Azioni:

* modifica
* attiva/disattiva
* run now
* elimina

---

## 9. Scheduler engine

## 9.1 Modalità di esecuzione

Nel backend FastAPI puoi avere un job loop avviato all’avvio app:

* ogni 15–30 secondi
* cerca schedule attive con `next_run_at <= now`
* per ciascuna:

  * acquisisce lock
  * verifica overlap
  * crea execution
  * aggiorna `last_run_at`, `last_status`, `last_execution_id`
  * calcola `next_run_at`

## 9.2 Lock

Se il container/backend può essere uno solo, basta lock applicativo leggero.
Se in futuro avrai più repliche, servirà lock DB.

Scelta consigliata già da ora:

* update atomico su riga schedulazione
* oppure campo `scheduler_locked_until`

V1 semplice:

* query transazionale
* select delle schedule dovute
* update immediato `next_run_at` o `locked_at`

## 9.3 Misfire policy

Se il backend è fermo e poi riparte, che fare delle run perse?

Opzioni:

* `fire_once_on_restart`
* `skip_missed_and_reschedule`

Consiglio V1:

* **skip missed and reschedule**
* più semplice, più controllato

---

## 10. Validazioni

### Creazione/modifica

* `test_suite_id` obbligatorio
* `frequency_mode` obbligatorio
* interval: `frequency_value > 0`
* weekly: almeno un weekday + `time_of_day`
* `start_at < end_at` se entrambi valorizzati

### Runtime

* non eseguire se `active = false`
* non eseguire se fuori finestra `start_at/end_at`
* non eseguire se overlap policy blocca

---

## 11. Estensioni future

Da mettere già in roadmap ma non in V1:

* cron expression
* email/notifiche su esito
* retry policy schedulazione
* blackout windows
* parametri/costanti schedule-specifiche
* target environment
* schedule templates
* pause temporanea fino a data
* dashboard storico schedule

Una feature molto utile in futuro è permettere che la schedule passi `constants` iniziali al run, coerentemente con il modello `runEnvelope.constants`. 

---

## 12. Decisioni consigliate per V1

Ti suggerisco questa V1:

* una nuova entità `test_suite_schedule`
* modalità supportate:

  * `interval`
  * opzionale `weekly`
* campi minimi:

  * suite
  * frequenza
  * attivo/disattivo
  * next_run_at
  * last_run_at
  * last_status
* overlap policy:

  * solo `skip`
* scheduler loop nel backend
* riuso completo dell’attuale esecuzione suite
* UI dedicata semplice

---

# PLAN operativo per Codex

## Intro tecnica

Implementare la schedulazione delle test suite come layer applicativo sopra il runtime già esistente delle suite.
La schedulazione non introduce un nuovo motore di esecuzione: deve solo determinare quando una suite va lanciata e invocare il servizio runtime attuale di esecuzione test suite.
La persistenza deve salvare configurazione schedule, stato attivo/disattivo, prossima esecuzione, ultima esecuzione ed esito ultimo lancio.
Il backend deve eseguire un loop scheduler periodico compatibile con deploy in container.
La UI deve permettere CRUD schedule, attivazione/disattivazione e run manuale immediato.
Questa scelta è coerente con il modello esistente di suite ed execution, e con il contesto runtime basato su `runEnvelope/global/local/result`.  

## Checklist

### Modello dati

* [ ] creare tabella `test_suite_schedules`
* [ ] aggiungere FK verso `test_suites`
* [ ] introdurre campi `active`, `frequency_mode`, `frequency_unit`, `frequency_value`
* [ ] introdurre campi `weekdays_json`, `time_of_day`
* [ ] introdurre campi `start_at`, `end_at`, `timezone`
* [ ] introdurre campi `next_run_at`, `last_run_at`, `last_status`, `last_execution_id`, `last_error_message`
* [ ] aggiungere audit `created_at`, `updated_at`

### Dominio e validazioni

* [ ] definire enum `frequency_mode`
* [ ] definire enum `frequency_unit`
* [ ] validare schedule interval
* [ ] validare schedule weekly
* [ ] validare finestra `start_at/end_at`
* [ ] definire funzione comune di calcolo `next_run_at`

### Backend API

* [ ] creare endpoint lista schedule
* [ ] creare endpoint dettaglio schedule
* [ ] creare endpoint creazione schedule
* [ ] creare endpoint modifica schedule
* [ ] creare endpoint cancellazione schedule
* [ ] creare endpoint activate
* [ ] creare endpoint deactivate
* [ ] creare endpoint `run-now`

### Scheduler runtime

* [ ] creare service `test_suite_scheduler_service`
* [ ] creare loop periodico interno al backend
* [ ] leggere schedule attive con `next_run_at <= now`
* [ ] verificare policy overlap
* [ ] invocare il servizio esistente di run suite
* [ ] aggiornare `last_run_at`, `last_status`, `last_execution_id`
* [ ] ricalcolare `next_run_at`
* [ ] salvare eventuale `last_error_message`

### Integrazione execution

* [ ] aggiungere metadato trigger `schedule` all’avvio esecuzione
* [ ] valorizzare `runEnvelope` con origine schedulata
* [ ] mantenere invariati hook/test/commands della suite
* [ ] esporre il collegamento tra schedule ed execution nei dettagli run

### UI Streamlit

* [ ] aggiungere pagina in Test sotto `Test suite` di nome `Schedules`
* [ ] creare lista schedulazioni con stato e prossima esecuzione
* [ ] creare form di inserimento/modifica
* [ ] supportare attiva/disattiva
* [ ] supportare `run now`
* [ ] mostrare ultima esecuzione e ultimo stato

### Test

* [ ] test unitari calcolo `next_run_at` interval
* [ ] test unitari calcolo `next_run_at` weekly
* [ ] test validazioni DTO schedule
* [ ] test API CRUD
* [ ] test attiva/disattiva
* [ ] test `run-now`
* [ ] test scheduler loop con suite dovuta
* [ ] test skip se suite già in running
* [ ] test aggiornamento `last_status`
* [ ] test restart backend con run missed e reschedule corretto

---

## Nota di design importante

Ti consiglio di non partire da espressioni cron libere.
Per Qsmith, lato utente/tester, è meglio un modello guidato e chiaro:

* ogni N minuti
* ogni N ore
* ogni N giorni
* certi giorni a una certa ora

