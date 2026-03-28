import { createReducer } from '@ngrx/store';

export interface AppState {
  initializedAt: string;
}

export const initialState: AppState = {
  initializedAt: new Date().toISOString()
};

export const appReducer = createReducer(initialState);
