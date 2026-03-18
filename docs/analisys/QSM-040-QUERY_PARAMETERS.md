# Dataset Parameters – Technical Design & Implementation Plan

## 🎯 Obiettivo

Introdurre un sistema di **parametri nei dataset** che consenta di:

* definire dataset riusabili
* filtrare i dati dinamicamente a runtime
* supportare schedulazioni (es. ogni 15 minuti)
* integrare i valori con:

  * costanti del contesto
  * valori calcolati runtime (es. `$now`)
  * override espliciti nei command

Il tutto senza esporre SQL libero all’utente finale.

---

## 🧩 Contesto

Esempio:

Tabella: `queue_message_received`

| campo       | tipo     |
| ----------- | -------- |
| id          | int      |
| payload     | json     |
| pipeline_id | string   |
| arrived_at  | datetime |

Use case:

* schedulazione ogni 15 minuti
* lettura dataset filtrato per:

  * `pipeline_id = $pipelineId`
  * `arrived_at <= $now`
* invio risultati su coda

---

## 🧱 Modello dati

### Estensione `DatasetPerimeter`

```json
{
  "selected_columns": ["id", "payload", "pipeline_id", "arrived_at"],
  "parameters": [
    {
      "name": "pipelineId",
      "type": "string",
      "required": true,
      "default_value": null,
      "default_resolver": "$pipelineId",
      "description": "Pipeline da filtrare"
    },
    {
      "name": "now",
      "type": "datetime",
      "required": true,
      "default_value": null,
      "default_resolver": "$now",
      "description": "Timestamp corrente"
    }
  ],
  "filter": {
    "logic": "AND",
    "conditions": [
      {
        "field": "pipeline_id",
        "operator": "eq",
        "value": {
          "kind": "parameter",
          "name": "pipelineId"
        }
      },
      {
        "field": "arrived_at",
        "operator": "lte",
        "value": {
          "kind": "parameter",
          "name": "now"
        }
      }
    ]
  },
  "sort": [
    {
      "field": "arrived_at",
      "direction": "asc"
    }
  ]
}
```

---

## 🔑 Concetti chiave

### 1. Parameter Definition

Definizione formale nel dataset:

* `name`
* `type`
* `required`
* `default_value`
* `default_resolver`

---

### 2. Parameter Reference (nei filtri)

NON usare stringhe tipo:

```json
"value": "$pipelineId"
```

MA usare struttura esplicita:

```json
"value": {
  "kind": "parameter",
  "name": "pipelineId"
}
```

✅ vantaggi:

* validazione forte
* UI guidata
* no ambiguità

---

### 3. Runtime Resolution

I parametri vengono risolti a runtime prima della query.

---

## ⚙️ Risoluzione parametri

### Ordine di precedenza

Per ogni parametro:

1. **override esplicito nel command**
2. **built-in resolver** (`$now`, `$today`, ecc.)
3. **context constants**

   * local
   * global
   * runEnvelope
4. **default_value**
5. ❌ errore se `required = true`
6. `null` se opzionale

---

### Built-in resolver supportati

* `$now` → timestamp corrente
* `$today` → data corrente
* (future) `$executionId`, `$runId`

---

### Context resolution

Ordine:

1. `local.constants`
2. `global.constants`
3. `runEnvelope.constants`

---

## 🧠 Esempio di risoluzione

Parametro:

```json
{
  "name": "pipelineId",
  "required": true,
  "default_resolver": "$pipelineId"
}
```

Runtime:

| Fonte            | Risultato |
| ---------------- | --------- |
| override command | ✅         |
| context constant | ✅         |
| default_value    | fallback  |
| none             | ❌ errore  |

---

Parametro:

```json
{
  "name": "now",
  "default_resolver": "$now"
}
```

→ sempre calcolato runtime

---

## 🔌 Integrazione con i command

### Esempio `initConstant`

```json
{
  "commandCode": "initConstant",
  "configuration": {
    "target": "messages",
    "sourceType": "Dataset",
    "datasetId": "ds_queue_message_received",
    "parameters": {
      "pipelineId": "PIPE_001"
    }
  }
}
```

---

### Variante avanzata (reference)

```json
"parameters": {
  "pipelineId": {
    "kind": "context_constant",
    "name": "pipelineId"
  }
}
```

---

## 🏗️ Runtime Flow

1. scheduler triggera la suite
2. viene creato `runEnvelope`
3. popolazione costanti (es. `pipelineId`)
4. command usa dataset
5. `DatasetParameterResolver`:

   * calcola valori finali
6. `DatasetPerimeterCompiler`:

   * genera query SQL parametrica
7. esecuzione query
8. risultati salvati in costante
9. action invia messaggi in coda

---

## 🧪 Validazioni

### A compile time

* [ ] parametro referenziato esiste
* [ ] tipo coerente con operatore
* [ ] no parametri non dichiarati

---

### A runtime

* [ ] parametro required risolto
* [ ] tipo corretto dopo risoluzione
* [ ] errore esplicito con dettagli

---

## 🧱 Componenti da implementare

### Backend

* [ ] `DatasetParameterDefinition`
* [ ] `DatasetParameterResolver`
* [ ] `BuiltInParameterResolver`
* [ ] `ContextParameterResolver`
* [ ] estensione `DatasetPerimeter`
* [ ] aggiornamento `DatasetPerimeterCompiler`
* [ ] binding SQL parametrico (no string interpolation)

---

### Command Layer

* [ ] supporto `parameters` nei command dataset-based
* [ ] parsing override parametri
* [ ] integrazione con context

---

### UI

#### Dataset editor

* [ ] sezione **Parameters**

  * nome
  * tipo
  * required
  * default
  * resolver

#### Filter builder

* [ ] toggle:

  * literal
  * parameter
* [ ] dropdown parametri

#### Command editor

* [ ] sezione “Parameter bindings”
* [ ] per ogni parametro:

  * dataset default
  * static value
  * context constant
  * built-in

---

## 🚨 Error handling

Formato errore consigliato:

```json
{
  "error": "DATASET_PARAMETER_RESOLUTION_FAILED",
  "datasetId": "ds_queue_message_received",
  "parameter": "pipelineId",
  "reason": "Parameter required but not resolved",
  "resolution_attempts": [
    "override",
    "built-in",
    "context",
    "default"
  ]
}
```

---

## 🔒 Sicurezza

* vietato SQL libero
* solo query generate
* uso di prepared statements
* escape automatico

---

## 🚀 Estensioni future

* [ ] parametri relativi (`now - 15m`)
* [ ] operatori `IN` con array
* [ ] preview dataset con input parametri
* [ ] parametri derivati (espressioni)
* [ ] supporto timezone
* [ ] caching dataset parametrico

---

## ✅ Checklist implementazione

* [ ] estendere modello `DatasetPerimeter`
* [ ] aggiungere `parameters`
* [ ] implementare resolver parametri
* [ ] implementare built-in resolver
* [ ] implementare context resolution
* [ ] integrare con command `initConstant`
* [ ] aggiornare compiler SQL
* [ ] aggiungere validazioni compile-time
* [ ] aggiungere validazioni runtime
* [ ] aggiornare UI dataset editor
* [ ] aggiornare UI filtri
* [ ] aggiornare UI command
* [ ] test unitari resolver
* [ ] test SQL generation
* [ ] test end-to-end con scheduler
