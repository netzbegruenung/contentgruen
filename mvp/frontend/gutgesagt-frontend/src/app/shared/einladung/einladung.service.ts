import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, map } from 'rxjs';
import { environment } from '../../../environments/environment';

// Grenzen wie im Backend (services/einladung_service.py).
export const EINLADUNG_NOTIZ_MAX = 200;
export const EINLADUNG_KONTEN_MAX = 1000;
export const EINLADUNG_TAGE_MAX = 366;

export type EinladungZustand = 'aktiv' | 'abgeschaltet' | 'abgelaufen' | 'aufgebraucht';

/** Eine Einladung, wie Admins sie im Admin-Dashboard sehen. */
export interface Einladung {
  id: string;
  code: string;
  notiz: string;
  erlaubte_konten: number;
  angelegte_konten: number;
  /** ISO-Datum (JJJJ-MM-TT), der letzte Tag, an dem sie gilt. */
  gueltig_bis: string;
  abgeschaltet: boolean;
  angelegt_am: string;
  zustand: EinladungZustand;
}

export interface EinladungListe {
  registrierung_eingerichtet: boolean;
  einladungen: Einladung[];
}

/** Der Link, den ein Admin weitergibt. Der Code steht hinter #, damit er in keinem Server-Log landet. */
export function einladungslink(code: string, origin = window.location.origin): string {
  return `${origin}/einladung#${code}`;
}

/**
 * Einladungen (#429). Verwalten duerfen nur Admins; pruefen und einloesen jede Person
 * mit dem Link, ohne Anmeldung.
 */
@Injectable({ providedIn: 'root' })
export class EinladungService {
  private baseUrl = `${environment.baseUrl}/api/v1/einladungen`;

  constructor(private http: HttpClient) {}

  liste(): Observable<EinladungListe> {
    return this.http.get<EinladungListe>(this.baseUrl);
  }

  anlegen(notiz: string, erlaubteKonten: number, gueltigBis: string): Observable<Einladung> {
    return this.http.post<Einladung>(this.baseUrl, {
      notiz,
      erlaubte_konten: erlaubteKonten,
      gueltig_bis: gueltigBis,
    });
  }

  schalten(id: string, abgeschaltet: boolean): Observable<Einladung> {
    return this.http.patch<Einladung>(`${this.baseUrl}/${id}`, { abgeschaltet });
  }

  pruefen(code: string): Observable<boolean> {
    return this.http
      .post<{ einloesbar: boolean }>(`${this.baseUrl}/pruefen`, { code })
      .pipe(map((antwort) => antwort.einloesbar));
  }

  einloesen(code: string, email: string): Observable<unknown> {
    return this.http.post(`${this.baseUrl}/einloesen`, { code, email });
  }
}
