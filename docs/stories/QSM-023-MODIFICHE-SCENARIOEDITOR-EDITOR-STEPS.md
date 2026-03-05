# QSM-023 - Modifiche ScenarioEditor - editor steps

## Stato
- Stato: Completato
- Checklist: 11/11 completata

## Dettaglio sviluppo

### Modifiche ScenarioEditor - editor steps

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

## Fonte
- Estratto da `docs/TASK.md`
