import { Component, signal } from '@angular/core';
import { DxDataGridModule } from 'devextreme-angular';

interface TestSuiteRow {
  id: string;
  name: string;
  tests: number;
  lastExecution: string;
  result: 'PASSED' | 'FAILED' | 'NOT_EXECUTED';
}

@Component({
  selector: 'qsm-test-suites-page',
  standalone: true,
  imports: [DxDataGridModule],
  template: `
    <section class="card">
      <h1>Test Suites</h1>
      <p>Vertical slice iniziale con griglia DevExtreme.</p>

      <dx-data-grid
        [dataSource]="rows()"
        [showBorders]="true"
        [columnAutoWidth]="true"
        [hoverStateEnabled]="true"
      >
        <dxo-paging [enabled]="true" [pageSize]="5"></dxo-paging>
        <dxo-filter-row [visible]="true"></dxo-filter-row>

        <dxi-column dataField="name" caption="Suite"></dxi-column>
        <dxi-column dataField="tests" caption="Tot test"></dxi-column>
        <dxi-column dataField="lastExecution" caption="Ultima esecuzione"></dxi-column>
        <dxi-column dataField="result" caption="Esito"></dxi-column>
      </dx-data-grid>
    </section>
  `
})
export class TestSuitesPage {
  readonly rows = signal<TestSuiteRow[]>([
    {
      id: 'suite-001',
      name: 'Smoke Payments',
      tests: 12,
      lastExecution: '2026-03-27 09:30',
      result: 'PASSED'
    },
    {
      id: 'suite-002',
      name: 'Regression Broker Queue',
      tests: 37,
      lastExecution: '2026-03-27 11:50',
      result: 'FAILED'
    },
    {
      id: 'suite-003',
      name: 'Nightly API MockServer',
      tests: 18,
      lastExecution: '2026-03-26 22:00',
      result: 'NOT_EXECUTED'
    }
  ]);
}
