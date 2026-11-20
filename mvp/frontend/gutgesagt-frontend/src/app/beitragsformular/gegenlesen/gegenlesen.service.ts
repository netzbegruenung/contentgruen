import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import type { Zweck } from '../../shared/zweck-stil';

/** Wartezeit nach der letzten Eingabe, bevor gegengelesen wird (#358: „etwa 1 s“). */
export const GEGENLESEN_VERZOEGERUNG_MS = 1000;

/** Eine Anmerkung beim Gegenlesen, wie `services/gegenlesen/gegenlesen_service.py` sie liefert. */
export interface Anmerkung {
  art:
    | 'verneinung'
    | 'schluesselwoerter'
    | 'satzlaenge'
    | 'statt_sag'
    | 'passiv'
    | 'kompositum'
    | 'gedankenstrich'
    | 'parteistimme'
    | 'titel_frage'
    | 'zahl_ohne_herkunft'
    | 'scheinbeleg'
    | 'herkunft_ohne_fundstelle'
    | 'erlebnis'
    | 'haeme'
    | 'floskel';
  stelle: 'titel' | 'text';
  text: string;
  woerter: string[];
  /** `false` bei einer Anmerkung ohne Abzug von der Güte (etwa das Erlebnis). */
  zaehlt?: boolean;
}

/** Wofür ein Kommentar geschrieben ist (`shared/zweck-stil.ts`). */
export type GegenlesenZweck = Zweck;

/** Optionale Angaben des Formulars, die das Gegenlesen genauer machen. */
export interface GegenlesenKontext {
  /**
   * Ob das Formular eine Herkunft hat; ``null`` ohne Herkunftsfeld (Post, Bild), dann
   * entfaellt die Regel zu Zahlen ohne Herkunft.
   */
  hatHerkunft?: boolean | null;
  /**
   * Eingetragen ist nur eine Startseite oder ein lokaler Pfad; das zaehlt als fehlende
   * Herkunft. Auch nur Ja/Nein, die Herkunft selbst geht nicht mit.
   */
  herkunftOhneFundstelle?: boolean;
  /** Fuer Gleichgesinnte zieht die Parteistimme nicht ab. */
  zweck?: GegenlesenZweck | null;
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

  gegenlesen(
    titel: string,
    text: string,
    aussage: string,
    titelIstBehauptung: boolean,
    { hatHerkunft = null, herkunftOhneFundstelle = false, zweck = null }: GegenlesenKontext = {},
  ): Observable<Gegengelesen> {
    return this.http.post<Gegengelesen>(this.url, {
      titel,
      text,
      aussage,
      titel_ist_behauptung: titelIstBehauptung,
      ...(hatHerkunft === null ? {} : { hat_herkunft: hatHerkunft }),
      ...(herkunftOhneFundstelle ? { herkunft_ohne_fundstelle: true } : {}),
      ...(zweck === null ? {} : { zweck }),
    });
  }
}
