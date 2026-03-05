# QSM-026 - Esecuzione step scenario

## Stato
- Stato: Completato
- Checklist: 9/9 completata

## Dettaglio sviluppo

### Esecuzione step scenario

- [x] creare architettura SSE (Server-Sent Events) fra Qsmith e Qsmith UI in modo tale che il BE possa inviare eventi al FE per aggiornarlo 
- [x] aggiungere bottone check\errore\pallino vuoto a fianco della label steptype (servirÃ  per capire se l'ultima esecuzione dello step Ã¨ andata a buon fine)
- [x] aggiungere bottone check\errore\pallino vuoto a fianco della descrizione dell'oprazione (servirÃ  per capire se l'ultima esecuzione dell'operazione Ã¨ andata a buon fine)
- [x] aggiungere pulsante per esecuzione singolo step alla maschera dello scenarioEditor nel container dello step a finaco ai bottoni add\import operation
- [x] alla pressione del botton di avvio mostrare dialog che richiede se eseguire anche i precedenti o solo il singolo ( in inglese )
- [x] aggiungere api per esecuzione di step scenario ( asincrona ) con aggiornamenti al FE
- [x] all'esecuzione dello step viene inviato l'esito (log) al FE
- [x] all'esecuzione dell'operazione viene inviato l'esito (log) al FE
- [x] in basso a destra un elemento che indichi "Test scenario running: 3/6 step executed"

## Fonte
- Estratto da `docs/TASK.md`
