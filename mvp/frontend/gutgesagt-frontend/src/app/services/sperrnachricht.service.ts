import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { environment } from '../../environments/environment';
import { Pruefung } from './moderation.service';

/**
 * Eine Sperrnachricht (Glossar): Entscheidung, Sperrgrund und Begründung zu einem
 * gesperrten Beitrag der angemeldeten Person, dazu ihr Widerspruch und das Ergebnis
 * der erneuten Prüfung, auch wenn die Sperre danach aufgehoben ist. Wer gesperrt hat,
 * steht nicht darin.
 */
export interface Sperrnachricht {
  id: string;
  content_id: string;
  content_type: string | null;
  /** null, wenn der Beitrag nicht mehr existiert. */
  titel: string | null;
  sperrgrund: string;
  begruendung: string;
  gesperrt_am: string | null;
  /** Gesetzt nur, wenn die Sperre nach dem Widerspruch aufgehoben wurde. */
  aufgehoben_am: string | null;
  widerspruch_am: string | null;
  pruefung: Pruefung | null;
  pruefung_begruendung: string | null;
  geprueft_am: string | null;
}

/** Sperrnachrichten lesen und widersprechen (/api/v1/sperren, #448). */
@Injectable({ providedIn: 'root' })
export class SperrnachrichtService {
  private baseUrl = `${environment.baseUrl}/api/v1/sperren`;

  constructor(private http: HttpClient) {}

  /** Die Sperrnachrichten der angemeldeten Person, die neueste zuerst. */
  meine(): Observable<Sperrnachricht[]> {
    return this.http
      .get<{ sperren: Sperrnachricht[] }>(`${this.baseUrl}/meine`)
      .pipe(map((antwort) => antwort.sperren));
  }

  /** Formlos widersprechen; der Text darf leer sein. */
  widersprechen(sperreId: string, text: string): Observable<{ success: boolean }> {
    return this.http.post<{ success: boolean }>(`${this.baseUrl}/${sperreId}/widerspruch`, {
      text: text.trim() || null,
    });
  }
}
