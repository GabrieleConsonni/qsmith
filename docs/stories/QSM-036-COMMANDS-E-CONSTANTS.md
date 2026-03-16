# CONTEXT, CONSTANTS e COMMANDS

Version: 1.0  
Target: Codex implementation  
Language: Python backend

# 1. Technical Overview

## CONTEXT: 
Rappresenta il contesto entro cui avvengono esecuzioni di test, commands e event trigger run.
Si suddivide gerarchicamente come :
- **runEnvelope**: generato da comando run context in api\queue mdi mock server
		{
			"run_id": "uuid",
			"event": {
				"id": "uuid",
				"mock_server_id": "",
				"listener_type": "api|queue",
				"listener_id":"",
				"trigger": {
					"code": "",
					"method": "",
					"queue_code": ""
				},
				"timestamp": "",
				"payload": {},
				"meta": {}
			},
			"constants": {}, <-- costanti in fase di lancio
		}
		Meta possibili:
			Rest API:
				meta.headers
				meta.query
				meta.path_params
			Queue:
				meta.message_attributes
				meta.message_id
- **global**: generato all'esecuzione dall'hook beforeAll della test suite
		{
			"runEnvelope": {} | None,
			"constants":{}
		}
- **local**: generato dall'esecuzione dell'hook before della test suite
		{
			"global":{},
			"constants":{}
		}
- **result_artifacts**:
		{
		}
			
## CONSTANTS:
Le costanti di contesto sono definibili con:
- **name**: sintassi json field 
- **type**: 
    - raw: tipi Python come number, str, dict etc.. ( dobbiamo cercare una nomeclatura tester friendly )
    - json
    - jsonArray è un id di jsonArray esistente 
    - dataset è un id di dataset esistente
    
- **context**: contesto di appartenenza
		runEnvelope
        global
		local
		result

## COMMANDS:
I commands sono entità eseguibili all'interno di determinati context. Sono divisi in famiglie: 
- **actions**: leggono variabili di contesto e inviano messaggi, scrivono tabelle etc.
- **context**: leggono sorgenti e aggiungono costanti al contesto di lavoro
- **asserts**: confrontano costanti di contesto con altre costanti e\o sorgenti di dati
	
### ACTION COMMANDS:
- **sendMessageQueue**: invia i dati contenuti in una costante in una coda.
	parametri:
		- coda SQS
		- template <-- il template per inviare il messaggio 
		- result target <-- costante del result context dove scrivere i risultati
- **saveTable**: salva i dati contenuti in una costante in una tabella interna a Qsmith.
	parametri:
		- nome tabella
- **dropTable** : elimina una tabella interna di Qsmith
- **cleanTable** : svuota una tabella interna di Qsmith 
- **exportDataset**: salva i dati contenuti in una costante in una tabella esterna e l'aggiunge ai dataset presenti su Qsmith.
	parametri:
	    - route della costante
	    - connessione
		- nome tabella
		- tipologia di export: drop\create, insert\update, append
		- mapping: se insert\update indicare quali elementi del 
		- descrizione data dataset
- **dropDataset**: elimina la tabella collegata al dataset e il dataset stesso
    parametri:
        - dataset id
- **cleanDataset**: svuola la tabella collegata al dataset 
    parametri:
        - dataset id
- **runSuite**: avvia una suite di test
	parametri:
		- id test suite
        - constants: [] <-- array di costanti attuali da salvare nel nuovo runEnvelope
		
### CONTEXT COMMANDS:
- **initConstant**: inizializza e salva una costante con i dati letti da una sorgente dati. Imposta il type in base al tipo sorgente. 
	parametri:
		- target <-- costante su cui sccrivere i dati
		- tipo di sorgente: 
			Raw : stringa, numero, date, datetime, dict
			JsonArray
				id di jsonArray salvato a db 
			SQSQueue
				id della SQSqueue esistente
				retry <-- numero tentativi in caso coda vuota
				wait_time_seconds
				max_messages <-- numero massimo di messaggi che si possono leggere
			Dataset 
				id del dataset
- **deleteConstant**: rimuove una costante 
    parametri:
        - target <-- la costante da salvare
				
### ASSERT:
Gli assert si dividono per il tipo di expect confrontato
- **jsonEquals( expected, actual)**: verifica che expected e actual siano uguali
		expected
			- json 
		actual 
			- costante del contesto
- **jsonEmpty\jsonNotEmpty(actual)**
		actual 
			- costante del contesto
- **jsonContains(expected, actual)**: nell'expected ci sono le properties e rispettivi valori dell'actual
		expected
			- json 
		actual 
			- costante del contesto
- **jsonArrayEquals( expected, actual)**: verifica che expected e actual siano uguali
		expected
			- id di jsonArray presente a db
		actual 
			- costante del contesto
- **jsonArrayEmpty\jsonArrayNotEmpty(actual)**
		actual 
			- costante del contesto
- **jsonArrayContains(expected, actual)**: nell'expected ci sono le properties e rispettivi valori dell'actual
		expected
			- json 
		actual 
			- costante del contesto
		

## SUDDIVISIONE COMMANDS:	

### MOCK SERVER :

- pre-response
	- initConstant
	- jsonEquals
	- jsonEmpty
	- jsonNotEmpty
	- jsonContains
	- jsonArrayEquals
	- jsonArrayEmpty
	- jsonArrayNotEmpty
	- jsonArrayContains

- post-response
	- sendMessageQueue
	- saveTable
	- exportTable
	- saveTable
	- dropTable
	- cleanTable
	- exportDataset
	- dropDataset
	- cleanDataset
	- runSuite	
		

### TEST SUITE:

- HOOKS:	
	- initConstant
	- deleteConstant
	- saveTable
	- dropTable
	- cleanTable
	- exportDataset
	- dropDataset
	- cleanDataset
	
- TEST
    - initConstant
	- sendMessageQueue
	- saveTable
	- exportTable
	- saveTable
	- dropTable
	- cleanTable
	- exportDataset
	- dropDataset
	- cleanDataset
	- jsonEquals
	- jsonEmpty
	- jsonNotEmpty
	- jsonContains
	- jsonArrayEquals
	- jsonArrayEmpty
	- jsonArrayNotEmpty
	- jsonArrayContains
	

## TEST SUITE CONSTANTS:
I fase di costruzione di un test le costanti create devono essere visibili e persistite.
Le costanti si riferiscono sempre ad un contesto: run, global, local, result.

Es:
- l'utente crea una initConstant in beforeAll con name B
- l'utente crea una initConstant in test con name A
- l'utente crea l'assert equals
- il sistema propone A e B come costante 

I context, actions e assert commands dentro hooks\test si riferiscono ai relativi contesti con i seguenti permessi: 
	- hooks: visibilita di contesto run e globale. 
		per beforeAll\afterAll scrittura su global
		per before scrittura su local dopo la creazione
		after lettura da local prima della sua distruzione.  
    - test: visibilità di contesto run, globale e locale. Scrittura solo locale. 

# PLAN

## REFACTOR BE:
[ ] cambiare naming operation in commands ( codice, database e ux )
[ ] introdurre CommandType: action, context, assert
[ ] refactor operations\commands esistenti
	
	Context:
		DataConfigurationOperationDto,
		DataFromJsonArrayConfigurationOperationDto,
		DataFromDbConfigurationOperationDto,
		DataFromQueueConfigurationOperationDto
			diventano InitContextConstantDto con sourceType differenti
	
	Actions:
		SleepConfigurationOperationDto --> diventa SleepActionDto
		PublishConfigurationOperationDto --> diventa SendSqsMessageActionDto
		SaveInternalDBConfigurationOperationDto --> diventa SaveTableActionDto
		SaveToExternalDBConfigurationOperationDto --> diventa ExportTableActionDto
		RunSuiteConfigurationOperationDto --> diventa RunSuiteActionDto
		
	Assert: 
		AssertConfigurationOperationDto --> diventa AssertDto 

[ ] rimuovere:
		SetResponseStatusConfigurationOperationDto
    	SetResponseHeaderConfigurationOperationDto
    	SetResponseBodyConfigurationOperationDto
    	BuildResponseFromTemplateConfigurationOperationDto

## COMMANDS MANCANTI
[ ] aggiungere i commands mancanti