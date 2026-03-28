import { Component, inject, signal } from '@angular/core';
import { Store } from '@ngrx/store';

import { AppState } from '../../state/app.reducer';

@Component({
  selector: 'qsm-home-page',
  standalone: true,
  template: `
    <div class="card">
      <h1>Nuova UI Angular avviata</h1>
      <p>
        Questa applicazione e' in esecuzione in parallelo alla UI Streamlit e costituisce la base
        del rollout incrementale.
      </p>
      <p><strong>Init store timestamp:</strong> {{ initializedAt() }}</p>
      <p><strong>Counter (Signal locale):</strong> {{ counter() }}</p>
      <button type="button" (click)="inc()">Incrementa counter</button>
    </div>
  `
})
export class HomePage {
  private readonly store = inject(Store<{ app: AppState }>);

  readonly counter = signal(0);
  readonly initializedAt = this.store.selectSignal((state) => state.app.initializedAt);

  inc(): void {
    this.counter.update((v) => v + 1);
  }
}
