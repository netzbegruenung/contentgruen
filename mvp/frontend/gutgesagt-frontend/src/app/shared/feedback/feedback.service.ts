import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

// Grenzen wie im Backend (services/feedback_service.py: TEXT_MAX, KONTAKT_MAX,
// AUFBEWAHRUNG_TAGE). Das Formular nennt die Frist, bevor gesendet wird.
export const FEEDBACK_TEXT_MAX = 2000;
export const FEEDBACK_KONTAKT_MAX = 200;
export const FEEDBACK_AUFBEWAHRUNG_TAGE = 180;

/** Feedback, wie Admins es im Admin-Dashboard sehen. */
export interface FeedbackEintrag {
  id: string;
  text: string;
  kontakt: string | null;
  /** ISO-Datum (JJJJ-MM-TT), nur der Tag. */
  eingegangen_am: string;
  /** Von einem Admin als bearbeitet markiert (#425); die Frist gilt trotzdem. */
  erledigt: boolean;
}

export interface FeedbackListe {
  aufbewahrung_tage: number;
  eintraege: FeedbackEintrag[];
}

/**
 * Feedback an das Team (#343). Senden darf jede Person, auch ohne Anmeldung;
 * die Liste sehen, als erledigt markieren und einzeln löschen nur Admins (#425).
 * Gespeichert wird nur Text, Kontakt und Tag, dazu der Merker „erledigt“.
 */
@Injectable({ providedIn: 'root' })
export class FeedbackService {
  private baseUrl = `${environment.baseUrl}/api/v1/feedback`;

  constructor(private http: HttpClient) {}

  senden(text: string, kontakt: string | null): Observable<unknown> {
    return this.http.post(`${this.baseUrl}/senden`, { text, kontakt });
  }

  /** Nur das offene (erledigt = false) oder nur das erledigte Feedback. */
  liste(erledigt: boolean): Observable<FeedbackListe> {
    const params = new HttpParams().set('erledigt', String(erledigt));
    return this.http.get<FeedbackListe>(this.baseUrl, { params });
  }

  erledigtSetzen(id: string, erledigt: boolean): Observable<FeedbackEintrag> {
    return this.http.patch<FeedbackEintrag>(`${this.baseUrl}/${encodeURIComponent(id)}`, { erledigt });
  }

  loeschen(id: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/${encodeURIComponent(id)}`);
  }
}
