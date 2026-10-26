import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class WorkflowService {
  private isOpen = new BehaviorSubject<boolean>(false);
  private currentWorkflow = new BehaviorSubject<string | null>(null);
  private workflowState = new Map<string, any>();

  isWorkflowOpen$ = this.isOpen.asObservable();
  currentWorkflow$ = this.currentWorkflow.asObservable();

  openWorkflow(type: string) {
    this.currentWorkflow.next(type);
    this.isOpen.next(true);
  }

  closeWorkflow() {
    this.currentWorkflow.next(null);
    this.isOpen.next(false);
  }

  saveWorkflowState(type: string, state: any) {
    this.workflowState.set(type, state);
  }

  getWorkflowState(type: string): any {
    return this.workflowState.get(type) || null;
  }

  resetWorkflowState(type: string) {
    this.workflowState.delete(type);
  }
}
