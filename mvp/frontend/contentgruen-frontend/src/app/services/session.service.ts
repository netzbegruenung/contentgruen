import { Injectable } from '@angular/core';

/**
 * Centralized service for managing anonymous user session IDs.
 * Used for tracking anonymous users across features like usage tracking and content reporting.
 */
@Injectable({
  providedIn: 'root'
})
export class SessionService {
  private readonly STORAGE_KEY = 'contentgruen_session_id';
  private sessionId: string | null = null;

  constructor() {
    // Initialize session ID on service creation
    this.sessionId = this.getOrCreateSessionId();
  }

  /**
   * Get the current session ID, creating one if it doesn't exist.
   * Session ID is stored in localStorage and persists across browser sessions.
   *
   * @returns The session ID string
   */
  getSessionId(): string {
    if (!this.sessionId) {
      this.sessionId = this.getOrCreateSessionId();
    }
    return this.sessionId;
  }

  /**
   * Generate a new session ID and store it.
   * This will replace any existing session ID.
   *
   * @returns The new session ID string
   */
  regenerateSessionId(): string {
    const newSessionId = this.generateSessionId();
    localStorage.setItem(this.STORAGE_KEY, newSessionId);
    this.sessionId = newSessionId;
    return newSessionId;
  }

  /**
   * Clear the current session ID from storage.
   * A new one will be generated on next access.
   */
  clearSessionId(): void {
    localStorage.removeItem(this.STORAGE_KEY);
    this.sessionId = null;
  }

  /**
   * Get existing session ID from storage or create a new one.
   * @private
   */
  private getOrCreateSessionId(): string {
    let sessionId = localStorage.getItem(this.STORAGE_KEY);

    if (!sessionId) {
      sessionId = this.generateSessionId();
      localStorage.setItem(this.STORAGE_KEY, sessionId);
    }

    return sessionId;
  }

  /**
   * Generate a UUID v4 compliant session ID.
   * @private
   */
  private generateSessionId(): string {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }
}
