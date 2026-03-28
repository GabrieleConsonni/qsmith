# qsmith-ui (Angular + DevExtreme)

Bootstrap iniziale della nuova UI Angular eseguita **in parallelo** alla UI Streamlit.

## Comandi

Dalla cartella `apps/qsmith-ui`:

```bash
npm install
npm run start
```

Altri comandi utili:

```bash
npm run build
npm run lint
```

## Stato iniziale

- Shell applicativa con sidebar e routing.
- Pagine iniziali: `Home` e `Test Suites`.
- `Test Suites` include una prima `dxDataGrid` DevExtreme.
- Stato globale base con NgRx + stato locale con Signals.
