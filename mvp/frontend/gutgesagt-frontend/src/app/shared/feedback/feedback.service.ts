import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

// Wie im Backend (services/feedback_service.py, AUFBEWAHRUNG_TAGE); das Formular
// nennt die Frist, bevor gesendet wird.
export const FEEDBACK_AUFBEWAHRUNG_TAGE = 180;

/** Feedback, wie Admins es im Admin-Dashboard sehen. */
export interface FeedbackEintrag {
  id: string;
  text: string;
  kontakt: string | null;
  /** ISO-Datum (JJJJ-MM-TT), nur der Tag. */
  eingegangen_am: string;
}

export interface FeedbackListe {
  aufbewahrung_tage: number;
  eintraege: FeedbackEintrag[];
}

/**
 * Feedback an das Team (#343). Senden darf jede Person, auch ohne Anmeldung;
 * die Liste sehen nur Admins. Gespeichert wird nur Text, Kontakt und Tag.
 */
@Injectable({ providedIn: 'root' })
export class FeedbackService {
  private baseUrl = `${environment.baseUrl}/api/v1/feedback`;

  constructor(private http: HttpClient) {}

  senden(text: string, kontakt: string | null): Observable<unknown> {
    return this.http.post(`${this.baseUrl}/senden`, { text, kontakt });
  }

  liste(): Observable<FeedbackListe> {
    return this.http.get<FeedbackListe>(this.baseUrl);
  }
}
