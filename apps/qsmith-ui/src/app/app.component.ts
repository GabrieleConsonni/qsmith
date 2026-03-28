import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

@Component({
  selector: 'qsm-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="layout-shell">
      <aside class="sidebar">
        <h2>QSmith UI</h2>
        <small>Angular + DevExtreme (parallelo Streamlit)</small>

        <nav style="margin-top: 1rem">
          <a routerLink="/home" routerLinkActive="active">Home</a>
          <a routerLink="/test-suites" routerLinkActive="active">Test Suites</a>
        </nav>
      </aside>

      <main class="content">
        <router-outlet></router-outlet>
      </main>
    </div>
  `
})
export class AppComponent {}
