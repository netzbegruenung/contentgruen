import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

/** Eine unbeantwortete Suchanfrage über der Schwelle, über die noch kein Admin entschieden hat. */
export interface ZuPruefendeSuchanfrage {
  statement_id: string;
  statement_text: string;
  /** Personen, die im Zeitraum ohne Treffer danach gesucht haben. */
  personen_ohne_treffer: number;
}

export interface ZuPruefendeSuchanfragenResponse {
  suchanfragen: ZuPruefendeSuchanfrage[];
}

export interface SuchanfrageEntscheidung {
  statement_id: string;
  freigegeben: boolean;
}

/**
 * Vormoderation (Entscheidung des Maintainers vom 13.11.2026): Unbeantwortete
 * Suchanfragen sehen Nicht-Admins erst nach Freigabe durch das Moderationsteam.
 * Nur für Admins; das Backend prüft die Rolle.
 */
@Injectable({ providedIn: 'root' })
export class SuchanfragenFreigabeService {
  private baseUrl = `${environment.baseUrl}/api/v1/moderation/suchanfragen`;

  constructor(private http: HttpClient) {}

  zuPruefen(): Observable<ZuPruefendeSuchanfragenResponse> {
    return this.http.get<ZuPruefendeSuchanfragenResponse>(this.baseUrl);
  }

  /** Nur die Zahl, für den Zähler am Umschalter; ohne Texte und billiger als die Liste. */
  anzahl(): Observable<{ anzahl: number }> {
    return this.http.get<{ anzahl: number }>(`${this.baseUrl}/anzahl`);
  }

  freigeben(statementId: string): Observable<SuchanfrageEntscheidung> {
    return this.http.put<SuchanfrageEntscheidung>(`${this.baseUrl}/${statementId}/freigeben`, {});
  }

  ablehnen(statementId: string): Observable<SuchanfrageEntscheidung> {
    return this.http.put<SuchanfrageEntscheidung>(`${this.baseUrl}/${statementId}/ablehnen`, {});
  }
}
