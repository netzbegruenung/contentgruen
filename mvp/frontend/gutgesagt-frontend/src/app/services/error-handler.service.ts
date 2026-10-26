import { Injectable, ErrorHandler } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';

@Injectable({
  providedIn: 'root'
})
export class GlobalErrorHandler implements ErrorHandler {
  constructor(private snackBar: MatSnackBar) {}

  handleError(error: Error): void {
    const errorMessage = this.getClientMessage(error);
    const stackTrace = this.getClientStack(error);

    // Log to console in development
    if (!this.isProduction()) {
      console.error('Global Error Handler:', error);
      console.error('Stack:', stackTrace);
    }

    // Show user-friendly message
    this.showErrorMessage(errorMessage);
  }

  private getClientMessage(error: Error): string {
    if (!navigator.onLine) {
      return 'Keine Internetverbindung. Bitte überprüfe dein Verbindung.';
    }

    if (error.message) {
      // Parse common error patterns
      if (error.message.includes('401')) {
        return 'Ihre Sitzung ist abgelaufen. Bitte melde dich erneut an.';
      }
      if (error.message.includes('403')) {
        return 'Du hast keine Berechtigung für diese Aktion.';
      }
      if (error.message.includes('404')) {
        return 'Die angeforderte Ressource wurde nicht gefunden.';
      }
      if (error.message.includes('500') || error.message.includes('502') || error.message.includes('503')) {
        return 'Ein Serverfehler ist aufgetreten. Bitte versuche es später erneut.';
      }

      // Return sanitized error message
      return error.message.length > 100
        ? 'Ein unerwarteter Fehler ist aufgetreten.'
        : error.message;
    }

    return 'Ein unerwarteter Fehler ist aufgetreten.';
  }

  private getClientStack(error: Error): string {
    return error.stack || '';
  }

  private showErrorMessage(message: string): void {
    this.snackBar.open(message, 'Schließen', {
      duration: 5000,
      horizontalPosition: 'center',
      verticalPosition: 'bottom',
      panelClass: ['error-snackbar']
    });
  }

  private isProduction(): boolean {
    // Check if we're in production mode
    return window.location.hostname !== 'localhost';
  }
}
