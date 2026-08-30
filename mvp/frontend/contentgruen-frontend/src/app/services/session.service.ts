import { Injectable } from '@angular/core';

/**
 * Centralized service for managing anonymous user session IDs.
 * Used for tracking anonymous users across features like usage tracking and content reporting.
 */
@Injectable({
  providedIn: 'root'
})
export class SessionService {
  private readonly STORAGE_KEY = 'gutgesagt_session_id';
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
   * Erzeugt eine UUID v4 als Session-Kennung.
   *
   * crypto.randomUUID() statt Math.random(): Math.random() ist nicht
   * kryptografisch sicher -- die Werte stammen aus einem vorhersagbaren
   * Generator, dessen Zustand sich aus wenigen Ausgaben rekonstruieren laesst.
   * Fuer eine Kennung, die anonyme Meldungen und Nutzungsereignisse
   * zusammenhaelt, ist Ratbarkeit die falsche Eigenschaft.
   *
   * crypto.randomUUID() gibt es in allen Browsern, die diese Anwendung
   * unterstuetzt, allerdings nur in einem sicheren Kontext (HTTPS oder
   * localhost). Der Fallback deckt den Rest ab und nutzt weiterhin
   * crypto.getRandomValues, also ebenfalls keine Math.random-Werte.
   *
   * @private
   */
  private generateSessionId(): string {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
      return crypto.randomUUID();
    }

    // Fallback fuer nicht-sichere Kontexte: dieselbe UUID-v4-Form, aber aus
    // crypto.getRandomValues statt aus Math.random.
    const bytes = new Uint8Array(16);
    crypto.getRandomValues(bytes);

    // Version (4) und Variante (10xx) nach RFC 4122 setzen.
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;

    const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
    return [
      hex.slice(0, 8),
      hex.slice(8, 12),
      hex.slice(12, 16),
      hex.slice(16, 20),
      hex.slice(20),
    ].join('-');
  }
}
