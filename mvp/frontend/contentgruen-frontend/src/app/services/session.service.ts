import { Injectable } from '@angular/core';

/**
 * Centralized service for managing anonymous user session IDs.
 * Used for tracking anonymous users across features like usage tracking and content reporting.
 *
 * Die Kennung laeuft nach 30 Tagen ab und wird beim naechsten Lesen neu vergeben.
 * Ohne Ablauf bliebe sie bei jemandem, der sich nie abmeldet, dauerhaft stabil und
 * verknuepfte damit saemtliche Nutzungsereignisse eines Browsers unbefristet.
 */
@Injectable({
  providedIn: 'root'
})
export class SessionService {
  private readonly STORAGE_KEY = 'gutgesagt_session_id';
  private readonly CREATED_AT_KEY = 'gutgesagt_session_id_created_at';
  private readonly MAX_AGE_MS = 30 * 24 * 60 * 60 * 1000; // 30 Tage

  /**
   * Get the current session ID, creating one if it doesn't exist or has expired.
   * Session ID is stored in localStorage and persists across browser sessions
   * until it reaches the maximum age.
   *
   * Bewusst ohne Zwischenspeicher im Feld: eine lange offene Seite wuerde eine
   * einmal gemerkte Kennung sonst ueber ihren Ablauf hinaus weiterverwenden.
   * Ein localStorage-Zugriff pro Suche oder Meldung faellt nicht ins Gewicht.
   *
   * @returns The session ID string
   */
  getSessionId(): string {
    return this.getOrCreateSessionId();
  }

  /**
   * Generate a new session ID and store it.
   * This will replace any existing session ID.
   *
   * @returns The new session ID string
   */
  regenerateSessionId(): string {
    return this.persistSessionId(this.generateSessionId());
  }

  /**
   * Clear the current session ID from storage.
   * A new one will be generated on next access.
   */
  clearSessionId(): void {
    localStorage.removeItem(this.STORAGE_KEY);
    localStorage.removeItem(this.CREATED_AT_KEY);
  }

  /**
   * Get existing session ID from storage or create a new one.
   * @private
   */
  private getOrCreateSessionId(): string {
    const sessionId = localStorage.getItem(this.STORAGE_KEY);

    if (!sessionId || this.isExpired()) {
      return this.persistSessionId(this.generateSessionId());
    }

    return sessionId;
  }

  /**
   * Check whether the stored session ID has outlived its maximum age.
   *
   * Eine Kennung ohne lesbaren Zeitstempel gilt als abgelaufen: das sind die vor
   * dieser Aenderung angelegten Kennungen, deren Alter sich nicht mehr feststellen
   * laesst und die deshalb unbegrenzt alt sein koennen.
   *
   * @private
   */
  private isExpired(): boolean {
    const createdAt = Number(localStorage.getItem(this.CREATED_AT_KEY));

    if (!Number.isFinite(createdAt) || createdAt <= 0) {
      return true;
    }

    return Date.now() - createdAt >= this.MAX_AGE_MS;
  }

  /**
   * Write session ID and its creation timestamp.
   *
   * Einziger Schreibpfad, damit kein Aufrufer den Zeitstempel vergessen kann --
   * eine Kennung ohne Zeitstempel waere sofort wieder abgelaufen.
   *
   * @private
   */
  private persistSessionId(sessionId: string): string {
    localStorage.setItem(this.STORAGE_KEY, sessionId);
    localStorage.setItem(this.CREATED_AT_KEY, String(Date.now()));
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
