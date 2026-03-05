# QSM-028 - Scenario executions

## Stato
- Stato: Completato
- Checklist: 11/11 completata

## Dettaglio sviluppo

### Scenario executions

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

## Fonte
- Estratto da `docs/TASK.md`
