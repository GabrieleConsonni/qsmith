# Piano operativo: migrazione UI da Streamlit ad Angular + DevExtreme

## 1) Obiettivo

Creare una nuova Single Page Application Angular + DevExtreme in **parallelo** all'attuale UI Streamlit, mantenendo invariato il backend esistente e riducendo il rischio operativo tramite rollout incrementale.

## 2) Perimetro e vincoli

- **Backend invariato nella prima fase**: le API attuali restano la fonte ufficiale.
- **Parità funzionale**: prima si raggiunge feature parity sulle funzioni core, poi si introducono miglioramenti UX.
- **Migrazione per moduli**: nessun "big-bang", ma rilascio graduale per aree funzionali.
- **Qualità**: test automatici su API contract, componenti Angular e flussi end-to-end.

## 3) Mappatura funzionale iniziale (Streamlit -> Angular)

Questa mappatura guida backlog e priorità della migrazione:

- `Home` -> dashboard Angular con card stato e ultimi run.
- `TestSuites` / `SuiteEditor` / `TestEditor` / `AdvancedSuiteEditorSettings` -> area principale Test Management.
- `TestSuiteSchedules` -> pagina scheduler con griglia DevExtreme.
- `Brokers` / `Queues` / `QueueDetails` -> area messaggistica con master/detail.
- `MockServers` / `MockServerEditor` -> area mock API/queue.
- `DatabaseConnections` / `Datasets` / `DatasetPerimeterEditor` -> area datasource.
- `JsonArray` / `Logs` -> utility operative.

## 4) Architettura target (Angular)

### 4.1 Stack suggerito

- Angular LTS (standalone components)
- DevExtreme + `devextreme-angular`
- NgRx **e** Signal Store: NgRx per i flussi enterprise cross-modulo, Signals per stato locale/presentazionale nei componenti feature.
- RxJS per orchestrazione chiamate API
- Cypress per E2E, Jest/Vitest per unit test

### 4.2 Struttura progetto (proposta)

- `apps/qsmith-ui` (SPA)
- `libs/core` (auth, interceptor, config, error handling)
- `libs/shared-ui` (componenti riusabili DevExtreme wrapper)
- `libs/features/*` (test-suites, brokers, mock-servers, datasets, logs...)
- `libs/api-client` (client OpenAPI generato)

### 4.3 Integrazioni chiave

- **OpenAPI codegen** per evitare drift del contratto backend.
- **Global HTTP interceptor** per error mapping, retry policy e tracing id.
- **Feature flags** per attivare moduli Angular in modo progressivo.

## 5) Piano di delivery per fasi

## Fase 0 - Assessment (1 settimana)

**Output**
- Inventario completo delle pagine Streamlit e relativi endpoint.
- Matrice priorità (alto valore / basso rischio).
- Definizione KPI di migrazione.

**Attività**
- Reverse engineering dei flussi UI più usati.
- Raccolta gap funzionali e debt tecnico UI.
- Definizione standard UX/UI per DevExtreme.

## Fase 1 - Fondazione frontend (1-2 settimane)

**Output**
- Workspace Angular pronto (CI, lint, test, env).
- Design system minimo DevExtreme.
- API client tipizzato.

**Attività**
- Bootstrap progetto, routing, layout shell.
- Implementazione autenticazione/sessione (se richiesta dal backend).
- Setup test pipeline (unit + e2e smoke).

## Fase 2 - Moduli core ad alto impatto (3-5 settimane)

**Priorità proposta**
1. Test Suites (elenco + editor base + run)
2. Logs
3. Brokers/Queues

**Output**
- Prime pagine Angular utilizzabili in ambiente dev/stage.
- Parità funzionale MVP sui flussi principali.

**Attività**
- Migrazione tabelle a `dxDataGrid` con filtri/paginazione.
- Form editor con validazioni client coerenti alle regole backend.
- Gestione feedback utente (toast, loading state, error banner).

## Fase 3 - Moduli secondari e consolidamento (2-4 settimane)

**Output**
- Copertura funzionale completa delle pagine Streamlit residue.
- Miglioramenti UX e performance.

**Attività**
- Migrazione Mock Servers, Datasets, JsonArray.
- Ottimizzazione bundle, lazy loading, caching query.
- Test regressione end-to-end cross-modulo.

## Fase 4 - Rollout in parallelo (1-2 settimane)

**Output**
- Go-live controllato della UI Angular in parallelo alla UI Streamlit.
- Piano rollback pronto.
- Convivenza operativa stabile tra le due UI, senza disattivazione della legacy.

**Attività**
- Canary release su utenti pilota.
- Monitoraggio errori frontend + API.
- Runbook operativo per incident handling.

## 6) Backlog tecnico iniziale (Top 12)

1. Creare monorepo Angular e convenzioni naming.
2. Integrare DevExtreme tema custom coerente al branding attuale.
3. Generare API client da specifica OpenAPI.
4. Implementare `CoreModule` (interceptor, error service, config loader).
5. Realizzare shell app (menu, breadcrumb, layout responsive).
6. Implementare modulo `test-suites` (lista + dettaglio base).
7. Implementare esecuzione suite con polling/SSE dove disponibile.
8. Implementare modulo `logs` con filtri avanzati.
9. Implementare modulo `brokers/queues` con dettaglio messaggi.
10. Aggiungere feature flags e routing condizionale.
11. Coprire happy path E2E per i 3 moduli core.
12. Setup monitoring frontend (error tracking + web vitals).

## 7) Strategia di coesistenza (transizione)

Per minimizzare rischio:

- Menu applicativo con link a moduli Angular e fallback a Streamlit per moduli non ancora migrati.
- Routing per dominio funzionale (es. `/ui-ng/test-suites` e `/ui-legacy/...`).
- Gestione sessione condivisa per evitare doppio login.

## 8) KPI e criteri di accettazione

### KPI suggeriti

- % pagine migrate (target 100%).
- % flussi core coperti da E2E (target >= 80%).
- Error rate frontend in produzione (target in riduzione sprint su sprint).
- Tempo medio operazioni chiave (esecuzione suite, ricerca log, gestione queue).

### Definition of Done per modulo

- Parità funzionale validata da business.
- Test unitari + E2E minimi superati.
- Accessibilità base (keyboard navigation + contrasto).
- Documentazione utente aggiornata.

## 9) Rischi principali e mitigazioni

- **Rischio**: deriva tra payload backend e frontend.
  - **Mitigazione**: codegen OpenAPI + contract tests in CI.
- **Rischio**: regressioni nei flussi operativi complessi.
  - **Mitigazione**: golden-path E2E + canary release.
- **Rischio**: tempi lunghi su Suite Editor (complessità alta).
  - **Mitigazione**: spezzare in milestone (read-only, edit base, hook avanzati).
- **Rischio**: bassa adozione utenti.
  - **Mitigazione**: onboarding guidato e feedback loop rapido.

## 10) Team e governance (minimo consigliato)

- 1 Tech Lead full-stack
- 2 Frontend engineer Angular
- 1 Backend engineer part-time (supporto API)
- 1 QA automation
- 1 Product owner

Cerimonie consigliate: planning settimanale, demo ogni sprint, retro quindicinale.

## 11) Piano operativo immediato (prossimi 10 giorni)

1. Workshop tecnico (2h) per definire architettura Angular target.
2. Freeze del contratto API critico (test suites, logs, queues).
3. Bootstrap repository frontend + CI base.
4. Creazione UI shell + navigation.
5. Implementazione primo vertical slice: `TestSuites list` con dati reali.
6. Demo interna e raccolta feedback.
7. Aggiornamento backlog con stime story-point.

## 12) Decisioni da prendere subito

- Angular state management combinato: NgRx + Signals.
- Strategia autenticazione/sessione tra legacy e nuova UI.
- Ordine definitivo migrazione moduli (valore business vs effort).
- Livello minimo di parity per dichiarare un modulo "migrato".

---

Se vuoi, nel prossimo step posso trasformare questo piano in:

1. **Roadmap sprint-by-sprint (8-10 sprint)**
2. **Epic + User Story già pronte per Jira**
3. **Template tecnico del progetto Angular (struttura cartelle + convenzioni)**
