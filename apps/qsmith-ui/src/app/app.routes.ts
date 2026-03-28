import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'home'
  },
  {
    path: 'home',
    loadComponent: () => import('./features/home/home.page').then((m) => m.HomePage)
  },
  {
    path: 'test-suites',
    loadComponent: () =>
      import('./features/test-suites/test-suites.page').then((m) => m.TestSuitesPage)
  }
];
