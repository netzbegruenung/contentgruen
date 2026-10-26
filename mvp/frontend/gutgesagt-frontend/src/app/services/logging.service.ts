import { Injectable } from '@angular/core';

export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3
}

@Injectable({
  providedIn: 'root'
})
export class LoggingService {
  private currentLogLevel: LogLevel = this.getInitialLogLevel();

  debug(message: string, ...args: any[]): void {
    this.log(LogLevel.DEBUG, message, args);
  }

  info(message: string, ...args: any[]): void {
    this.log(LogLevel.INFO, message, args);
  }

  warn(message: string, ...args: any[]): void {
    this.log(LogLevel.WARN, message, args);
  }

  error(message: string, error?: Error, ...args: any[]): void {
    this.log(LogLevel.ERROR, message, args);
    if (error) {
      console.error(error);
    }
  }

  logError(message: string, error?: any, ...args: any[]): void {
    // Alias for error method for backward compatibility
    this.error(message, error, ...args);
  }

  logInteraction(action: string, details?: any): void {
    // Log user interactions at INFO level
    const message = `User interaction: ${action}`;
    if (details) {
      this.info(message, details);
    } else {
      this.info(message);
    }
  }

  private log(level: LogLevel, message: string, args: any[]): void {
    if (level >= this.currentLogLevel) {
      const timestamp = new Date().toISOString();
      const logMessage = `[${timestamp}] [${LogLevel[level]}] ${message}`;

      switch (level) {
        case LogLevel.DEBUG:
          console.debug(logMessage, ...args);
          break;
        case LogLevel.INFO:
          console.info(logMessage, ...args);
          break;
        case LogLevel.WARN:
          console.warn(logMessage, ...args);
          break;
        case LogLevel.ERROR:
          console.error(logMessage, ...args);
          break;
      }
    }
  }

  private getInitialLogLevel(): LogLevel {
    if (typeof (window as any).__karma__ !== 'undefined') {
      return LogLevel.WARN;
    }
    return this.isProduction() ? LogLevel.ERROR : LogLevel.DEBUG;
  }

  private isProduction(): boolean {
    return window.location.hostname !== 'localhost';
  }
}
