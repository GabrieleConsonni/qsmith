Perfetto, ti preparo un **markdown operativo per Codex** focalizzato solo sulla gestione **json + rimozione campi**, coerente con tutto il modello che stai costruendo.

---

# 📄 QSM – SendMessageQueue: JSON Field Filtering

## 🎯 Obiettivo

Permettere all’utente di utilizzare una variabile di tipo `json` come source per `sendMessageQueue` e **decidere quali campi rimuovere** dal payload prima dell’invio.

Questo approccio:

* riduce la dimensione del payload
* evita l’invio di dati sensibili o inutili
* rende il messaggio più controllato e leggibile ([JSONViewerTool][1])

---

## 🧩 UX – Form

### Quando `source = json`

Mostrare una nuova sezione:

### **Message filtering (optional)**

* Tipo: toggle (ON/OFF)

Se ON:

#### Modalità filtro

Radio:

* `Remove fields` (default)
* `Keep only fields` (future, opzionale)

---

### 🔹 Remove fields (prima versione)

UI:

| Field path      | Action |
| --------------- | ------ |
| [text / select] | ❌      |

* `+ Add field` per aggiungere altri campi

---

## 🧠 Field path

Supportare:

* campi root:

  ```
  id
  name
  ```

* campi nested (dot notation):

  ```
  customer.id
  metadata.token
  ```

👉 coerente con best practice standard JSON filtering ([JSONViewerTool][1])

---

## ⚙️ Comportamento runtime

### Input

```json
{
  "id": 1,
  "customer": {
    "id": "C01",
    "name": "Mario"
  },
  "metadata": {
    "token": "abc",
    "ip": "127.0.0.1"
  }
}
```

### Config

```json
{
  "removeFields": [
    "metadata.token",
    "customer.name"
  ]
}
```

### Output

```json
{
  "id": 1,
  "customer": {
    "id": "C01"
  },
  "metadata": {
    "ip": "127.0.0.1"
  }
}
```

---

## 🧱 Backend – funzione di filtro

### Python (pseudo)

```python
def remove_fields(data: dict, paths: list[str]) -> dict:
    for path in paths:
        keys = path.split(".")
        current = data

        for key in keys[:-1]:
            if key not in current:
                current = None
                break
            current = current[key]

        if current and keys[-1] in current:
            del current[keys[-1]]

    return data
```

---

## 🔁 Integrazione con command

### Flusso `sendMessageQueue`

```python
payload = source_json

if remove_fields_config:
    payload = remove_fields(payload, remove_fields_config)

send(payload)
```

---

## ⚠️ Edge cases

* path inesistente → ignorato (no errore)
* campo già assente → ignorato
* nested non oggetto → ignorato

👉 comportamento resiliente

---

## 🧪 Validazione UI

* evitare text libero puro (in futuro)
* miglioramento suggerito:

  * parser JSON → mostra struttura
  * select guidata dei campi

---

