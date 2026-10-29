import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

/** Wartezeit nach der letzten Eingabe, bevor gegengelesen wird (#358: „etwa 1 s“). */
export const GEGENLESEN_VERZOEGERUNG_MS = 1000;

/** Eine Anmerkung beim Gegenlesen, wie `services/gegenlesen/gegenlesen_service.py` sie liefert. */
export interface Anmerkung {
  art: 'verneinung' | 'schluesselwoerter' | 'satzlaenge' | 'statt_sag' | 'passiv' | 'kompositum';
  stelle: 'titel' | 'text';
  text: string;
  woerter: string[];
}

export interface Gegengelesen {
  /** Kriterienanteil der Güte, 1–10; `null`, solange Titel und Text leer sind. */
  guete: number | null;
  anmerkungen: Anmerkung[];
}

/** Gegenlesen ohne KI (#358). Nichts davon wird gespeichert. */
@Injectable({ providedIn: 'root' })
export class GegenlesenService {
  private url = `${environment.baseUrl}/api/v1/gegenlesen`;

  constructor(private http: HttpClient) {}

  gegenlesen(titel: string, text: string, aussage: string, titelIstBehauptung: boolean): Observable<Gegengelesen> {
    return this.http.post<Gegengelesen>(this.url, { titel, text, aussage, titel_ist_behauptung: titelIstBehauptung });
  }
}
