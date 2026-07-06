import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';

@Component({
  selector: 'app-error-message',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatButtonModule],
  template: `
    <mat-card class="error-card" *ngIf="error">
      <mat-card-content>
        <div class="error-content">
          <mat-icon class="error-icon">error_outline</mat-icon>
          <div class="error-text">
            <h3>{{ title || 'Ein Fehler ist aufgetreten' }}</h3>
            <p>{{ error }}</p>
          </div>
        </div>
        <button mat-button color="primary" *ngIf="showRetry" (click)="onRetry()">
          <mat-icon>refresh</mat-icon>
          Erneut versuchen
        </button>
      </mat-card-content>
    </mat-card>
  `,
  styles: [`
    .error-card {
      margin: 20px;
      background-color: #ffebee;
    }
    .error-content {
      display: flex;
      align-items: center;
      gap: 16px;
    }
    .error-icon {
      color: #c62828;
      font-size: 48px;
      width: 48px;
      height: 48px;
    }
    .error-text h3 {
      margin: 0 0 8px 0;
      color: #c62828;
    }
    .error-text p {
      margin: 0;
      color: rgba(0, 0, 0, 0.7);
    }
  `]
})
export class ErrorMessageComponent {
  @Input() error: string = '';
  @Input() title: string = '';
  @Input() showRetry: boolean = false;
  @Input() retryAction?: () => void;

  onRetry(): void {
    if (this.retryAction) {
      this.retryAction();
    }
  }
}
