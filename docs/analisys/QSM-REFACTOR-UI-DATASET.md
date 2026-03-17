# Refactor UI Dataset

## Obiettivo 
Rendere più leggibile e configurabile la maschera dei dataset

## Modifiche a Datasets.py
La lista di dataset diventa una lista di expander closed con descrizione dataset
Al loro interno:
Database :
Schema :
Tabella\View :
Bottone preview | Bottone Perimeter | Bottone modifica
Eventuale Preview

Il bottone modifica permette di modificare la descrizione e la configurazione con dialog come adesso
Il bottone perimeter apre nuova pagina DatasetPerimeterEditor.py

## DatasetPerimeterEditor.py

### Layout
<- torna ai dataset
Descrizione Dataset
vutoto | bottone salva e preview
divider
sezione colonne (come in dialog di adesso)
preview | sezione sort
sezione filters



