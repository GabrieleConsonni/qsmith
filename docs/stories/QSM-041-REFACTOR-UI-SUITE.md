# Refactor UI Dataset

## Obiettivo 
Rendere più leggibile e configurabile la maschera dei suite 

## Modifiche a SuiteEditor.py
Rimane solo la sezione test, rimuovere i pulsanti simil tabs.
Rimuovere container con i risultati esecuzione
Rimuovere bottone ... a destra dell'expander e aggiungerlo a fianco del bottone + Add assert

In alto a dx, a fianco del bottone esegui mettere rotellina con help "Advance settings".
Esso porta a nuova pagina AdvancedSuiteEditorSettings.py

## AdvancedSuiteEditorSettings.py

### Layout
<- torna alla suite
Advanced settings
divider
sezione Before suite
    eventuali commands
sezione Before each test
    eventuali commands
sezione After each test
    eventuali commands
sezione After suite
    eventuali commands