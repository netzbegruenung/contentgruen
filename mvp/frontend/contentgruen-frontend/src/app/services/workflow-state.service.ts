import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class WorkflowStateService {
  private states = new Map<string, any>();

  setState(key: string, state: any) {
    this.states.set(key, state);
  }

  getState(key: string): any {
    return this.states.get(key) || null;
  }

  clearState(key: string) {
    this.states.delete(key);
  }
}
