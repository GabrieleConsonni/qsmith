# Mock Server - Import e Sync da Swagger/OpenAPI

## Introduzione tecnica

Implementare una funzionalità di import e sincronizzazione delle API mock a partire da specifiche Swagger/OpenAPI esterne.

La feature deve integrarsi sopra il modello attuale dei Mock Server senza modificarne il runtime. Il flusso di esecuzione rimane invariato:

* `pre_response_commands`
* generazione response
* `post_response_commands`

L’import OpenAPI deve quindi occuparsi esclusivamente di:

* generare configurazioni API mock
* mantenerne il collegamento con una sorgente esterna
* permettere sincronizzazione futura con logica diff-based

È fondamentale preservare tutte le personalizzazioni locali fatte dall’utente (command, integrazioni, comportamento runtime).

---

## Obiettivi

* Importare API da Swagger/OpenAPI remoto
* Permettere import totale o selettivo (subset di API)
* Collegare le API a una sorgente esterna
* Permettere sincronizzazione manuale futura
* Non sovrascrivere configurazioni runtime custom

---

## Concetti chiave

### Modalità import

* **One-shot**

  * Import una tantum
  * Nessuna sincronizzazione futura

* **Managed**

  * API collegate alla sorgente
  * Possibilità di sync manuale

---

### Import selettivo

L’utente deve poter scegliere:

* [ ] Importare **tutte le API**
* [ ] Importare **solo un sottoinsieme**

Filtri possibili:

* per `tag`
* per `operationId`
* selezione manuale (checkbox per riga)

---

## Modello dati

### Tabella `mock_server_api_sources`

* [ ] `id`
* [ ] `mock_server_id`
* [ ] `source_type` (openapi)
* [ ] `source_url`
* [ ] `auth_type`
* [ ] `auth_configuration_json`
* [ ] `fetch_headers_json`
* [ ] `etag`
* [ ] `source_hash`
* [ ] `last_fetched_at`
* [ ] `last_sync_at`
* [ ] `last_sync_status`
* [ ] `last_sync_message`
* [ ] `created_at`
* [ ] `updated_at`

---

### Estensione API mock

* [ ] `source_id`
* [ ] `source_operation_id`
* [ ] `source_method`
* [ ] `source_path`
* [ ] `imported_from_source` (boolean)
* [ ] `sync_mode` (`manual | managed`)
* [ ] `sync_snapshot_hash`
* [ ] `local_overrides_json`
* [ ] `orphaned_from_source` (boolean)

---

## Parsing OpenAPI

### OpenApiImportService

* [ ] supportare JSON
* [ ] supportare YAML
* [ ] validare OpenAPI 3.x
* [ ] supporto base Swagger 2.0 (opzionale)
* [ ] risolvere `$ref`
* [ ] normalizzare:

  * path
  * method
  * parameters
  * requestBody
  * responses

---

### Dati estratti

* [ ] `operationId`
* [ ] `summary`
* [ ] `tags`
* [ ] `method`
* [ ] `path`
* [ ] path params
* [ ] query params
* [ ] header params
* [ ] request body schema/example
* [ ] response status principali
* [ ] response example/schema

---

## Mapping verso Mock Server

* [ ] creare route mock per ogni operation

* [ ] mappare method + path

* [ ] configurare parametri

* [ ] generare response default:

  * da `example`
  * fallback da `schema`
  * fallback vuoto

* [ ] NON toccare:

  * pre_response_commands
  * post_response_commands
  * integrazioni con queue
  * suite/test collegati

---

## Import Flow

### Endpoint

* [ ] `POST /mock-server/{id}/api-source/openapi/preview`
* [ ] `POST /mock-server/{id}/api-source/openapi/import`

---

### Preview

* [ ] fetch spec
* [ ] parsing
* [ ] lista operations

Ogni riga:

* method
* path
* operationId
* summary
* tag
* checkbox selezione

---

### Configurazione import

* [ ] URL spec
* [ ] auth type
* [ ] headers custom
* [ ] modalità (`one-shot` / `managed`)
* [ ] scelta:

  * [ ] tutte le API
  * [ ] selezione manuale

---

### Import

* [ ] creare `mock_server_api_source`
* [ ] salvare snapshot
* [ ] creare API mock selezionate
* [ ] collegarle alla source
* [ ] settare `sync_mode`

---

## Sync Flow

### Endpoint

* [ ] `POST /mock-server/{id}/api-source/{source_id}/sync-preview`
* [ ] `POST /mock-server/{id}/api-source/{source_id}/sync`

---

### Matching

* [ ] usare `operationId` se presente
* [ ] fallback `method + normalized_path`

---

### Diff

Classificare:

* [ ] `new`
* [ ] `updated`
* [ ] `removed`
* [ ] `unchanged`
* [ ] `conflict`

---

### Regole sync

* [ ] aggiornare solo campi spec-owned:

  * method
  * path
  * parametri
  * schema
  * response default

* [ ] NON aggiornare:

  * commands
  * integrazioni runtime
  * override locali

* [ ] NON cancellare automaticamente API mancanti

* [ ] marcare come `orphaned_from_source`

---

## UI (Streamlit)

### Mock Server Detail

* [ ] tab `API Sources`

---

### Import dialog

* [ ] input URL
* [ ] auth config
* [ ] modalità import
* [ ] scelta:

  * import tutto
  * import selettivo

---

### Preview UI

* [ ] tabella operations
* [ ] checkbox per riga
* [ ] filtro per tag
* [ ] select all / deselect all

---

### Sync UI

* [ ] tabella diff
* [ ] stato per riga
* [ ] checkbox apply
* [ ] evidenza conflitti
* [ ] opzione "mantieni override locali"

---

## Sicurezza

* [ ] gestire auth verso spec
* [ ] timeout fetch
* [ ] retry
* [ ] validazione URL
* [ ] protezione SSRF (allowlist)
* [ ] limitare dimensione spec
* [ ] audit log import/sync

---

## Test

* [ ] parsing JSON OpenAPI
* [ ] parsing YAML
* [ ] risoluzione `$ref`
* [ ] import totale
* [ ] import selettivo
* [ ] filtro per tag
* [ ] generazione example da schema
* [ ] sync `new`
* [ ] sync `updated`
* [ ] sync `removed`
* [ ] preservazione commands locali
* [ ] modalità `manual`
* [ ] modalità `managed`

---

## Roadmap futura

* [ ] sync schedulata
* [ ] multi-source per mock server
* [ ] supporto webhook/callback OpenAPI
* [ ] miglior generazione example
* [ ] supporto avanzato security schema

---

Se vuoi, nel prossimo step possiamo:

* definire lo schema JSON interno “normalizzato” dell’OpenAPI (molto utile per il parser)
* oppure disegnare direttamente le classi Python (`pydantic`) per implementarlo velocemente nel tuo servizio.
