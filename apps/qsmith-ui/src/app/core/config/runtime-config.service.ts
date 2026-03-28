import { Injectable, signal } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class RuntimeConfigService {
  readonly apiBaseUrl = signal<string>('http://localhost:8000');

  setApiBaseUrl(value: string): void {
    this.apiBaseUrl.set(value);
  }
}
