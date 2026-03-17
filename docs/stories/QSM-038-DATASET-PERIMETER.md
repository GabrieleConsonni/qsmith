# Qsmith - Dataset Perimeter Implementation

## Overview

Introduzione del concetto di **perimetro del dataset**, che consente di definire in modo controllato e sicuro:

- colonne da estrarre (projection)
- filtri (row filtering)
- ordinamento (sorting)

Il dataset diventa quindi una **vista logica parametrizzata** sopra una tabella/view del database.

Obiettivi:
- evitare SQL libero lato utente
- garantire sicurezza (no SQL injection)
- migliorare performance riducendo il dataset letto
- rendere il dataset riusabile e consistente

---

## Scope

Il perimetro deve essere applicato in:

- preview dataset (UI)
- runtime (es. initConstant → source Dataset)

---

## Data Model

### Nuovo tabella datataset
Rimuovere la tipologia dataset da json_payloads e aggiungere la tabella datasets:

id text
description text
configuration JSONB <--- mantiene la struttura dei dataset precedenti
perimeter JSONB nullable
created_date timestamp
modified_date timestamp

### Struttura perimeter

```json
{
  "selected_columns": ["col1", "col2"],
  "filter": {
    "logic": "AND",
    "conditions": [
      {
        "field": "status",
        "operator": "eq",
        "value": "READY"
      }
    ]
  },
  "sort": [
    {
      "field": "created_at",
      "direction": "desc"
    }
  ]
}
```

---

## Functional Requirements

### 1. Selected Columns

#### Regole

* se vuoto → tutte le colonne
* solo colonne esistenti
* no duplicati
* ordine rispettato

---

### 2. Filter

#### Struttura

```json
{
  "logic": "AND",
  "conditions": [
    {
      "field": "amount",
      "operator": "gt",
      "value": 100
    }
  ]
}
```

#### Operator supportati (MVP)

* eq
* neq
* gt
* gte
* lt
* lte
* contains
* starts_with
* ends_with
* in
* not_in
* is_null
* is_not_null

#### Regole

* `field` obbligatorio
* `operator` obbligatorio
* `value` obbligatorio (tranne is_null / is_not_null)
* `in/not_in` → array non vuoto

---

### 3. Sort

#### Struttura

```json
[
  {"field": "created_at", "direction": "desc"}
]
```

#### Regole

* direction: `asc | desc`
* colonne valide

---

## Backend Design

### DatasetPerimeterCompiler

Creare componente dedicato:

```python
class DatasetPerimeterCompiler:
    def compile(dataset, perimeter_json) -> Query
```

### Responsabilità

* validazione
* generazione query SQL parametrica
* protezione SQL injection
* adattamento DB (Postgres, ecc.)

---

## Query Generation

### Esempio output

```sql
SELECT order_id, status
FROM public.orders
WHERE status = :p1
ORDER BY created_at DESC
```

### Regole

* NO string concatenation
* usare binding parametri
* escaping automatico

---

## Validation Rules

### Selected Columns

* devono esistere nel metadata DB

### Filter

* campo esistente
* operatore valido
* tipo compatibile (best effort)

### Sort

* campo esistente
* direction valida

---

## API Changes

### Dataset CRUD

Aggiungere campo:

```json
"perimeter": { ... }
```

---

### Preview Dataset

* applicare perimetro
* limit risultati: 100 righe

---

## Runtime Integration

### initConstant
Quando `initConstant` usa source `Dataset`:

1. leggere dataset
2. leggere `perimeter`
3. compilare query
4. eseguire query
5. salvare risultato in variabile

### actions
Quando un action usa una variabile di tipo `Dataset`
1. leggere dataset
2. leggere `perimeter`
3. compilare query
4. eseguire query
5. esegue l'azione

---

## UI (Streamlit)

### Sezione: Datasets

#### Colonne

* multiselect colonne
* select all / reset

#### Filtri

* tabella editabile:

  * field
  * operator
  * value
* selettore AND/OR

#### Sort

* lista ordinamenti:

  * field
  * direction

---

### Preview

* mostra dati
* max 100 righe
* opzionale: mostra query logica

---

## Performance Considerations

* ridurre colonne
* filtrare presto
* evitare SELECT * se possibile

---

## Security

* vietato SQL raw utente
* validazione server-side obbligatoria
* query sempre parametrizzate

---

## Checklist

* [ ] aggiunta campo `perimeter` su dataset
* [ ] aggiornamento API CRUD
* [ ] implementazione DatasetPerimeterCompiler
* [ ] validazione server-side
* [ ] query builder parametrico
* [ ] preview dataset con limit
* [ ] integrazione initConstant
* [ ] UI sezione Perimetro
* [ ] test selected_columns
* [ ] test filter operators
* [ ] test sort multiplo
* [ ] test sicurezza (SQL injection)