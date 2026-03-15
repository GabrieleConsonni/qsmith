# Use Case Operazioni - Scenari Reali

## Scopo
Questo documento raccoglie use case funzionali per verificare le operation runtime di Qsmith con scenari realistici, sia nel contesto `test suite` sia nel contesto `mock server`.

## Copertura

| Operation / family | Scenari coperti |
| --- | --- |
| `data` | payload statici di input |
| `data-from-json-array` | caricamento dataset di riferimento |
| `data-from-db` | lettura dati da datasource tabellare |
| `data-from-queue` | lettura messaggi da queue |
| `sleep` | attesa controllata nel flusso |
| `publish` | invio messaggi verso queue |
| `save-internal-db` | audit e persistenza interna |
| `save-external-db` | export verso DB esterno |
| `assert` | `not-empty`, `equals`, `contains`, `json-array-equals`, `schema-validation` |
| `set-var` | preparazione variabili di contesto |
| `run-suite` | orchestrazione tra suite |
| `set-response-*` | costruzione response mock |
| `build-response-from-template` | response mock dinamica da template |

## Use case

### UC-OP-01 - Creazione payload ordine con `data` e validazione con `assert equals`
- [ ] Obiettivo: verificare che un test possa partire da un payload statico e confrontarlo con un valore atteso.
- [ ] Operation coperte: `data`, `assert`.
- [ ] Scenario reale: simulazione di un ordine creato manualmente da un tester.
- [ ] Precondizione: esiste una test suite con un test vuoto.
- [ ] Precondizione: il test puo leggere e scrivere il contesto `local`.
- [ ] Configurare una operation `data` che carica un JSON ordine in `$.local.order`.
- [ ] Configurare una operation `assert` con `assert_type=equals`.
- [ ] Confrontare `$.local.order.status` con il valore atteso `NEW`.
- [ ] Eseguire il test.
- [ ] Verificare che il payload venga scritto nel contesto locale.
- [ ] Verificare che l'assert termini con successo.
- [ ] Verificare che il risultato dell'assert sia tracciato negli artifacts di esecuzione.

### UC-OP-02 - Verifica catalogo prodotti con `data-from-json-array` e `assert contains`
- [ ] Obiettivo: verificare caricamento di dati di riferimento da datasource JSON array.
- [ ] Operation coperte: `data-from-json-array`, `assert`.
- [ ] Scenario reale: validazione che un prodotto presente in ordine esista nel catalogo prodotti di test.
- [ ] Precondizione: esiste un datasource JSON array `PRODUCT_CATALOG`.
- [ ] Precondizione: esiste una suite con un test che contiene il prodotto da cercare.
- [ ] Configurare `data-from-json-array` per leggere `PRODUCT_CATALOG` in `$.local.catalog`.
- [ ] Configurare un payload ordine con SKU noto.
- [ ] Aggiungere una `assert` di tipo `contains` usando `expected_json_array_id`.
- [ ] Impostare `compare_keys` su `sku`.
- [ ] Eseguire il test.
- [ ] Verificare che il catalogo venga caricato correttamente.
- [ ] Verificare che il record con SKU atteso venga trovato.
- [ ] Verificare che il test fallisca con errore chiaro se il prodotto non esiste.

### UC-OP-03 - Recupero ordini aperti da database con `data-from-db` e `assert not-empty`
- [ ] Obiettivo: verificare lettura da datasource tabellare e controllo di presenza dati.
- [ ] Operation coperte: `data-from-db`, `assert`.
- [ ] Scenario reale: controllo che il DB applicativo contenga ordini in stato `OPEN`.
- [ ] Precondizione: esiste un datasource DB configurato per la tabella o query degli ordini.
- [ ] Precondizione: il database contiene almeno una riga coerente con il filtro del dataset.
- [ ] Configurare `data-from-db` con il dataset ordini aperti.
- [ ] Scrivere il risultato in `$.local.open_orders`.
- [ ] Aggiungere una `assert` di tipo `not-empty`.
- [ ] Eseguire il test.
- [ ] Verificare che il datasource restituisca una collection valorizzata.
- [ ] Verificare che l'assert confermi che il risultato non e vuoto.
- [ ] Verificare che in caso di dataset vuoto il test si chiuda in errore.

### UC-OP-04 - Lettura messaggi evento da queue con `data-from-queue` e `schema-validation`
- [ ] Obiettivo: verificare consumo messaggi da queue e validazione della struttura JSON.
- [ ] Operation coperte: `data-from-queue`, `assert`.
- [ ] Scenario reale: verifica di messaggi `OrderCreated` pubblicati su una coda SQS locale.
- [ ] Precondizione: esiste una queue configurata con almeno un messaggio JSON valido.
- [ ] Precondizione: e disponibile uno schema JSON di riferimento.
- [ ] Configurare `data-from-queue` con `queue_id`, `retry`, `wait_time_seconds` e `max_messages`.
- [ ] Scrivere il risultato in `$.local.received_messages`.
- [ ] Aggiungere una `assert` con `assert_type=schema-validation`.
- [ ] Eseguire il test.
- [ ] Verificare che il test recuperi i messaggi dalla queue.
- [ ] Verificare che il payload ricevuto rispetti lo schema dichiarato.
- [ ] Verificare che se il payload e malformato l'errore venga mostrato nel dettaglio del test.

### UC-OP-05 - Preparazione variabili di contesto con `set-var`
- [ ] Obiettivo: verificare la creazione di variabili riusabili nel flusso.
- [ ] Operation coperte: `set-var`.
- [ ] Scenario reale: estrazione di `order_id` e `tenant` da un input iniziale per riusarli in operazioni successive.
- [ ] Precondizione: il test ha gia in contesto un payload ordine o un evento mock.
- [ ] Configurare `set-var` con `key=order_id` e `value` risolto dal payload.
- [ ] Configurare `set-var` con `key=tenant`.
- [ ] Eseguire il test.
- [ ] Usare i valori salvati in una operation successiva.
- [ ] Verificare che le variabili vengano rese disponibili nel contesto ammesso dallo scope.
- [ ] Verificare che i valori siano riutilizzabili da `publish`, `run-suite` o `assert`.
- [ ] Verificare che se lo scope non consente scrittura `global`, il runtime applichi la policy corretta.

### UC-OP-06 - Pubblicazione evento di conferma con `publish`
- [ ] Obiettivo: verificare invio di un messaggio verso una queue e salvataggio dell'esito tecnico.
- [ ] Operation coperte: `publish`.
- [ ] Scenario reale: pubblicazione di un evento `OrderConfirmed` dopo validazioni positive.
- [ ] Precondizione: esiste una queue di output configurata.
- [ ] Precondizione: il test dispone di dati ordine nel contesto locale.
- [ ] Configurare `publish` con `queue_id` della queue di destinazione.
- [ ] Usare `template_id` o `template_params` coerenti con il messaggio atteso.
- [ ] Salvare il risultato in `$.local.publish_result`.
- [ ] Eseguire il test.
- [ ] Verificare la presenza del messaggio in coda.
- [ ] Verificare che il messaggio venga pubblicato correttamente.
- [ ] Verificare che il risultato tecnico sia salvato nel target configurato.
- [ ] Verificare che l'eventuale errore di publish interrompa il test in fail-fast.

### UC-OP-07 - Audit interno con `save-internal-db`
- [ ] Obiettivo: verificare persistenza dati in una tabella interna dell'applicazione.
- [ ] Operation coperte: `save-internal-db`.
- [ ] Scenario reale: salvataggio di una riga di audit dopo l'elaborazione di un ordine.
- [ ] Precondizione: esiste una tabella interna dedicata ad audit o tracing.
- [ ] Precondizione: il test possiede un payload valido da salvare.
- [ ] Configurare `save-internal-db` con `table_name`.
- [ ] Impostare `result_target` su `$.local.audit_result`.
- [ ] Eseguire il test.
- [ ] Verificare su DB che la riga sia stata inserita.
- [ ] Verificare che l'inserimento avvenga con successo.
- [ ] Verificare che il risultato tecnico dell'operazione venga salvato nel contesto locale.
- [ ] Verificare che il record scritto sia coerente con i dati del test.

### UC-OP-08 - Export su sistema esterno con `save-external-db`
- [ ] Obiettivo: verificare persistenza su connessione database esterna.
- [ ] Operation coperte: `save-external-db`.
- [ ] Scenario reale: export ordini pronti per il sistema ERP.
- [ ] Precondizione: esiste una connessione DB esterna valida.
- [ ] Precondizione: esiste la tabella di destinazione nel DB esterno.
- [ ] Configurare `save-external-db` con `connection_id` e `table_name`.
- [ ] Salvare l'output tecnico in `$.local.external_save_result`.
- [ ] Eseguire il test.
- [ ] Verificare che la riga sia presente nel DB esterno.
- [ ] Verificare che l'operazione usi la connessione selezionata.
- [ ] Verificare che i dati vengano scritti nella tabella di destinazione.
- [ ] Verificare che l'eventuale errore di connessione sia riportato nel dettaglio esecuzione.

### UC-OP-09 - Attesa controllata con `sleep` prima di una lettura asincrona
- [ ] Obiettivo: verificare che il runtime rispetti una pausa esplicita tra due step.
- [ ] Operation coperte: `sleep`, opzionalmente `data-from-queue`.
- [ ] Scenario reale: attesa di pochi secondi prima di controllare la presenza di un messaggio prodotto da un sistema esterno.
- [ ] Precondizione: esiste un test che dipende da un evento asincrono non immediato.
- [ ] Configurare una operation `sleep` con durata nota.
- [ ] Inserire dopo la pausa una `data-from-queue`.
- [ ] Eseguire il test.
- [ ] Verificare che il runtime attenda la durata configurata.
- [ ] Verificare che la lettura successiva parta solo dopo l'attesa.
- [ ] Verificare che l'uso di `sleep` non alteri il contesto business.

### UC-OP-10 - Confronto completo dataset atteso con `assert json-array-equals`
- [ ] Obiettivo: verificare confronto tra dataset prodotto e dataset atteso.
- [ ] Operation coperte: `data-from-db` o `data-from-json-array`, `assert`.
- [ ] Scenario reale: confronto tra righe esportate e baseline di regressione.
- [ ] Precondizione: esiste un JSON array atteso di baseline.
- [ ] Precondizione: il test produce o legge una collection confrontabile.
- [ ] Caricare i dati reali in `$.local.actual_rows`.
- [ ] Configurare una `assert` con `assert_type=json-array-equals`.
- [ ] Impostare `expected_json_array_id` e `compare_keys`.
- [ ] Eseguire il test.
- [ ] Verificare che i dataset vengano confrontati sulle chiavi dichiarate.
- [ ] Verificare che il test passi solo se i contenuti sono equivalenti.
- [ ] Verificare che eventuali differenze generino un fallimento interpretabile.

### UC-OP-11 - Orchestrazione di una suite figlia con `run-suite`
- [ ] Obiettivo: verificare avvio di una suite secondaria e passaggio dati iniziali.
- [ ] Operation coperte: `run-suite`, `set-var`.
- [ ] Scenario reale: dopo la ricezione di un ordine, viene lanciata una suite separata di fulfillment.
- [ ] Precondizione: esiste una suite target identificabile da `suite_id` o `suite_code`.
- [ ] Precondizione: il test corrente dispone delle variabili da propagare.
- [ ] Preparare `order_id` con `set-var`.
- [ ] Configurare `run-suite` con `suite_code=FULFILL_ORDER`.
- [ ] Passare `init_vars` con i valori necessari.
- [ ] Salvare il risultato in `$.local.child_suite_result`.
- [ ] Eseguire il test.
- [ ] Verificare che la suite figlia venga avviata correttamente.
- [ ] Verificare che le `init_vars` vengano propagate alla nuova run.
- [ ] Verificare che il legame tra run chiamante e run figlia sia tracciabile.

### UC-OP-12 - Response dinamica mock con `set-response-status`, `set-response-header`, `set-response-body`
- [ ] Obiettivo: verificare costruzione incrementale della response in scope `mock.response`.
- [ ] Operation coperte: `set-response-status`, `set-response-header`, `set-response-body`.
- [ ] Scenario reale: mock API che riceve un ordine e restituisce `202 Accepted` con header di tracking.
- [ ] Precondizione: esiste un mock server API attivo.
- [ ] Precondizione: e configurata una route che usa response operations.
- [ ] Configurare `set-response-status` a `202`.
- [ ] Configurare `set-response-header` con `x-correlation-id`.
- [ ] Configurare `set-response-body` con body JSON coerente con l'evento ricevuto.
- [ ] Inviare una richiesta HTTP al mock.
- [ ] Verificare che la response usi status, header e body configurati via operation.
- [ ] Verificare che il body sia costruito con dati coerenti al trigger.
- [ ] Verificare che la route non usi fallback statico se le response operations sono presenti.

### UC-OP-13 - Response mock costruita da template con `build-response-from-template`
- [ ] Obiettivo: verificare costruzione di una response completa da template dinamico.
- [ ] Operation coperte: `build-response-from-template`.
- [ ] Scenario reale: endpoint mock che restituisce una conferma ordine con campi valorizzati dall'evento.
- [ ] Precondizione: esiste una route mock che usa `mock.response`.
- [ ] Precondizione: il template contiene placeholder o riferimenti risolvibili.
- [ ] Configurare `build-response-from-template` con `template`, `status` e `headers`.
- [ ] Inviare una request con payload ordine.
- [ ] Verificare la response ricevuta.
- [ ] Verificare che la response finale venga costruita a partire dal template.
- [ ] Verificare che i valori dinamici siano risolti correttamente.
- [ ] Verificare che il formato restituito sia coerente con il contratto API simulato.

### UC-OP-14 - Blocco di operation non ammesse nello scope
- [ ] Obiettivo: verificare enforcement della policy runtime per scope e side effects.
- [ ] Operation coperte: `publish`, `set-response-body`, `set-var`.
- [ ] Scenario reale: prevenzione di configurazioni errate nei mock o nei test.
- [ ] Precondizione: esiste un mock server con `pre_response_operations`.
- [ ] Precondizione: esiste una test suite standard.
- [ ] Configurare `publish` in `mock.preResponse`.
- [ ] Eseguire la route mock.
- [ ] Configurare `set-response-body` dentro uno scope `test`.
- [ ] Eseguire il test.
- [ ] Configurare `set-var` in un test con tentativo di scrittura su `global`.
- [ ] Verificare che `publish` venga bloccata in `mock.preResponse` per policy.
- [ ] Verificare che `set-response-body` non venga accettata nello scope `test`.
- [ ] Verificare che la scrittura non consentita su `global` venga rifiutata dal runtime.
- [ ] Verificare che gli errori siano espliciti e tracciati.

## Note operative
- [ ] Gli scenari possono essere usati come base per checklist manuali, test API o suite automatiche.
- [ ] Per test affidabili conviene predisporre prima i dati su datasource, queue e DB.
- [ ] Le operation con side effect (`publish`, `save-internal-db`, `save-external-db`, `run-suite`) vanno sempre verificate anche con controlli esterni al runtime, ad esempio query DB o lettura queue.
- [ ] Le operation `set-response-*` e `build-response-from-template` hanno senso solo in scope `mock.response`.
