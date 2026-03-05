# QSM-018 - Gestione Scenario_steps

## Stato
- Stato: Completato
- Checklist: 2/2 completata

## Dettaglio sviluppo

### Gestione Scenario_steps

- [x] Nella crud degli scenari, per ogni container di scenario sulla sinistra, mettere bottone esegui
- [x] In fase di aggiunta di uno step aprire dialog:
    - mettere selectbox con scelta steps esistenti
    - + per eventuale nuovo step
    - in caso di scelta di step esistente:
        - mostrare i dati dello step in sola lettura 
        - abilitare bottone con `add` 
    - in caso di scelta nuovo step 
        - abilitare i campi per l'inserimento (seguire ConfigurationStepDto)
        - abilitare bottone `save and add`
    - al salvataggio renderizzare nuovo step

## Fonte
- Estratto da `docs/TASK.md`
