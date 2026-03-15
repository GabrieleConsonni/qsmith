# Use Case Funzionali - Test Suite e Test

## Scopo
Questo documento elenca use case funzionali riutilizzabili per validare il dominio `test suite` e `test` di Qsmith, sia in test manuali sia come base per future test suite automatiche.

## Ambito
- [ ] gestione anagrafica `test_suites`
- [ ] gestione item embedded (`suite_items`)
- [ ] gestione operazioni del test (`suite_item_operations`)
- [ ] hook fissi `beforeAll`, `beforeEach`, `afterEach`, `afterAll`
- [ ] esecuzione singolo test
- [ ] esecuzione suite completa
- [ ] regole di contesto `global` e `local`
- [ ] feedback di esecuzione ed errori

## Use case

### UC-TS-01 - Creazione di una test suite vuota
- [ ] Obiettivo: verificare che una suite possa essere creata con i dati minimi richiesti.
- [ ] Precondizione: utente nella sezione `Test Suites`.
- [ ] Aprire la creazione di una nuova suite.
- [ ] Inserire codice e descrizione validi.
- [ ] Salvare senza aggiungere test.
- [ ] Verificare che la suite venga salvata correttamente.
- [ ] Verificare che la suite compaia in elenco.
- [ ] Verificare che siano disponibili i 4 hook fissi anche se vuoti.

### UC-TS-02 - Modifica dei dati base della suite
- [ ] Obiettivo: verificare aggiornamento persistente dei metadati della suite.
- [ ] Precondizione: esiste una suite salvata.
- [ ] Aprire la suite in modifica.
- [ ] Aggiornare descrizione o altri campi editabili.
- [ ] Salvare e ricaricare la pagina.
- [ ] Verificare che i nuovi valori siano persistiti.
- [ ] Verificare che nessun test o hook esistente venga perso.

### UC-TS-03 - Aggiunta di un test embedded alla suite
- [ ] Obiettivo: verificare che i test siano creati come `suite_items` embedded nella suite.
- [ ] Precondizione: esiste una suite.
- [ ] Aprire la suite.
- [ ] Selezionare `Add new test`.
- [ ] Inserire codice, descrizione e configurazione del test.
- [ ] Salvare.
- [ ] Verificare che il test compaia nella suite editor.
- [ ] Verificare che il test sia parte della suite senza dipendere da un catalogo `tests` esterno.
- [ ] Verificare che il test sia modificabile dalla suite stessa.

### UC-TS-04 - Configurazione di operazioni in un test
- [ ] Obiettivo: verificare che un test possa contenere una sequenza ordinata di operazioni.
- [ ] Precondizione: esiste una suite con almeno un test.
- [ ] Aprire un test della suite.
- [ ] Aggiungere operazioni di tipo input, output o assert.
- [ ] Salvare la suite.
- [ ] Riaprire il test.
- [ ] Verificare che le operazioni siano mostrate nel test in ordine.
- [ ] Verificare che i dati configurati restino persistiti.
- [ ] Verificare che la sequenza sia pronta per l'esecuzione runtime.

### UC-TS-05 - Configurazione degli hook della suite
- [ ] Obiettivo: verificare che i 4 hook fissi siano configurabili e persistiti.
- [ ] Precondizione: esiste una suite.
- [ ] Configurare almeno una operazione in `beforeAll`.
- [ ] Configurare almeno una operazione in `beforeEach`.
- [ ] Configurare almeno una operazione in `afterEach`.
- [ ] Configurare almeno una operazione in `afterAll`.
- [ ] Salvare e riaprire la suite.
- [ ] Verificare che ogni hook mantenga le proprie operazioni.
- [ ] Verificare che gli hook restino distinti dai test normali.
- [ ] Verificare che non sia possibile creare hook aggiuntivi oltre ai 4 previsti.

### UC-TS-06 - Esecuzione del singolo test
- [ ] Obiettivo: verificare l'esecuzione asincrona di un solo test dalla suite.
- [ ] Precondizione: esiste una suite con almeno un test eseguibile.
- [ ] Aprire la suite editor.
- [ ] Avviare l'esecuzione del singolo test.
- [ ] Attendere il completamento.
- [ ] Verificare che venga eseguito solo il test selezionato nel suo ciclo previsto.
- [ ] Verificare che gli indicatori di stato si aggiornino.
- [ ] Verificare che l'esito finale del test sia visibile con eventuale messaggio di errore.

### UC-TS-07 - Esecuzione della suite completa
- [ ] Obiettivo: verificare il workflow completo `beforeAll -> beforeEach -> test -> afterEach -> afterAll`.
- [ ] Precondizione: esiste una suite con almeno due test e hook valorizzati.
- [ ] Avviare l'esecuzione dell'intera suite.
- [ ] Monitorare l'avanzamento.
- [ ] Aprire il dettaglio esecuzione al termine.
- [ ] Verificare che `beforeAll` venga eseguito una sola volta all'inizio.
- [ ] Verificare che `beforeEach` e `afterEach` vengano eseguiti per ogni test.
- [ ] Verificare che `afterAll` venga eseguito una sola volta alla fine.
- [ ] Verificare che l'avanzamento mostri test eseguiti e totale.

### UC-TS-08 - Isolamento del contesto locale tra test
- [ ] Obiettivo: verificare che i test siano atomici e non condividano il contesto locale.
- [ ] Precondizione: suite con almeno due test che scrivono in `local`.
- [ ] Nel primo test salvare un valore nel contesto locale.
- [ ] Nel secondo test tentare di leggere quel valore senza reinizializzarlo.
- [ ] Eseguire la suite completa.
- [ ] Verificare che il secondo test non veda il contesto locale del primo.
- [ ] Verificare che ogni test usi un contesto locale autonomo.
- [ ] Verificare che il contesto locale venga distrutto a fine `afterEach`.

### UC-TS-09 - Utilizzo del contesto globale dagli hook
- [ ] Obiettivo: verificare che gli hook possano preparare dati condivisi per i test.
- [ ] Precondizione: suite con `beforeAll` o `beforeEach` configurato.
- [ ] Salvare un valore nel contesto `global` da un hook.
- [ ] Leggere quel valore in un test.
- [ ] Eseguire suite o test interessato.
- [ ] Verificare che il valore scritto dall'hook sia disponibile in lettura nei test.
- [ ] Verificare che la risoluzione del dato sia coerente nel runtime.
- [ ] Verificare che il dato resti disponibile secondo il lifecycle previsto.

### UC-TS-10 - Blocco scrittura del contesto globale durante il test
- [ ] Obiettivo: verificare la regola che impedisce ai test di modificare `global`.
- [ ] Precondizione: suite con un test che tenta di scrivere su `$.global.*`.
- [ ] Configurare un'operazione nel test che scrive nel contesto globale.
- [ ] Eseguire il singolo test.
- [ ] Verificare che l'esecuzione fallisca o venga bloccata dalla policy runtime.
- [ ] Verificare che il messaggio di errore spieghi che il test non puo scrivere su `global`.
- [ ] Verificare che il contesto globale non venga alterato.

### UC-TS-11 - Tracciamento esiti e storico esecuzioni
- [ ] Obiettivo: verificare la persistenza degli esiti di suite, test e operazioni.
- [ ] Precondizione: almeno una suite eseguita.
- [ ] Aprire la sezione delle esecuzioni della suite.
- [ ] Espandere una esecuzione.
- [ ] Consultare esito della suite, dei test e delle operazioni.
- [ ] Verificare che l'esecuzione mostri testata con esito globale e data/ora.
- [ ] Verificare che ogni test mostri il proprio esito.
- [ ] Verificare che ogni operazione mostri il proprio esito ed eventuale errore.

### UC-TS-12 - Riesecuzione dopo errore con pulizia feedback
- [ ] Obiettivo: verificare che una nuova esecuzione riparta da uno stato pulito.
- [ ] Precondizione: esiste una suite con una esecuzione precedente fallita.
- [ ] Correggere la configurazione che aveva causato l'errore.
- [ ] Rieseguire il test o la suite.
- [ ] Osservare indicatori e messaggi durante la nuova run.
- [ ] Verificare che i feedback della run precedente vengano azzerati all'avvio.
- [ ] Verificare che i nuovi esiti sostituiscano quelli vecchi.
- [ ] Verificare che non restino errori stale a video se la nuova esecuzione termina con successo.

## Note operative
- [ ] Gli use case possono essere eseguiti sia da UI sia via API, se il flusso disponibile lo consente.
- [ ] Per i casi runtime e consigliato preparare dati di test su broker, datasource o mock server prima dell'esecuzione.
- [ ] Per regressioni mirate conviene coprire sempre almeno: creazione suite, aggiunta test, esecuzione singolo test, esecuzione suite completa, isolamento contesti, blocco scrittura `global`.
