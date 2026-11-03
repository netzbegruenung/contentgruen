import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../../environments/environment';

/** Wartezeit nach der letzten Eingabe, wie beim Gegenlesen. */
export const SPRACHHINWEIS_VERZOEGERUNG_MS = 1000;

/**
 * Ab so vielen Wörtern fragt das Formular, wie `MIN_WOERTER` in
 * `services/spracherkennung/spracherkennung.py`: Auf kürzeren Texten ist die Erkennung unsicher.
 */
export const SPRACHHINWEIS_AB_WOERTERN = 5;

/** Buchstaben am Stück; Zahlen, Zeichen und Emoji zählen nicht (wie im Dienst). */
export function woerterZaehlen(text: string): number {
  return text.match(/\p{L}+/gu)?.length ?? 0;
}

/** Spracherkennung beim Schreiben (#405). Nichts davon wird gespeichert. */
@Injectable({ providedIn: 'root' })
export class SprachhinweisService {
  private url = `${environment.baseUrl}/api/v1/spracherkennung`;

  constructor(private http: HttpClient) {}

  /** Die Sprache (ISO 639-1), wenn der Text offenbar nicht deutsch ist, sonst `null`. */
  fremdsprache(text: string): Observable<{ sprache: string | null }> {
    return this.http.post<{ sprache: string | null }>(this.url, { text });
  }
}
