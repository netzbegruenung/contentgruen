import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, Subject, of } from 'rxjs';
import { catchError, concatMap, map, shareReplay, tap } from 'rxjs/operators';
import { environment } from '../../environments/environment';
import {
  AussageMitThemen,
  AussagenMitThemenResponse,
  Thema,
  ThemenResponse,
  ThemenTestsetResponse,
  ThemenZuordnenRequest,
  ThemenZuordnenResponse,
} from './dtos/themenDtos';

/** Wie im Backend (domain/themen.py): eine Aussage hat hoechstens zwei Themen. */
export const HOECHSTENS_THEMEN_JE_AUSSAGE = 2;

/** Eine angezeigte Aussage mit ihren Themen, wie sie die Listen fuehren. */
export interface AussageMitThemenFeld {
  statement_id: string;
  themen: Thema[];
}

/** Die Schluessel von Themen, fuer <app-themen-auswahl [gewaehlt]>. */
export function schluesselVon(themen: Thema[]): string[] {
  return themen.map((t) => t.schluessel);
}

/**
 * Die Themen: die feste Liste und ihre Zuordnung zu Aussagen. Zuordnen darf jede
 * angemeldete Person; die Liste aller Aussagen zum Zuordnen und das Testset
 * sehen nur Admins.
 */
@Injectable({ providedIn: 'root' })
export class ThemenService {
  private readonly basis = `${environment.baseUrl}/api/v1/statement/themen`;
  private liste$?: Observable<Thema[]>;
  /** Je angezeigter Aussage die Warteschlange ihrer Aenderungen (aendern). */
  private readonly warteschlangen = new WeakMap<AussageMitThemenFeld, Subject<string[]>>();

  constructor(private http: HttpClient) {}

  /** Die feste Liste, einmal je Sitzung geladen; sie aendert sich nur mit einem Release. */
  liste(): Observable<Thema[]> {
    this.liste$ ??= this.http.get<ThemenResponse>(this.basis).pipe(
      map((antwort) => antwort.themen),
      shareReplay({ bufferSize: 1, refCount: false }),
    );
    return this.liste$;
  }

  /** Die Themen einer Aussage setzen; ersetzt die bisherigen. Liefert, was jetzt gilt. */
  zuordnen(statementId: string, themen: string[]): Observable<Thema[]> {
    const request: ThemenZuordnenRequest = { statement_id: statementId, themen };
    return this.http
      .put<ThemenZuordnenResponse>(`${this.basis}/zuordnen`, request)
      .pipe(map((antwort) => antwort.themen));
  }

  /**
   * Die Themen einer angezeigten Aussage aendern, wie sie ein Themen-Waehler meldet.
   * Die Anzeige folgt sofort, damit ein zweiter schneller Klick auf dem ersten
   * aufbaut. Gespeichert wird der Reihe nach, damit am Ende der letzte Klick gilt;
   * ist nichts mehr offen, zeigt die Aussage den zuletzt gespeicherten Stand. Das
   * ist nach einem Fehler der Stand vor dem gescheiterten Klick, und `fehler` wird gerufen.
   */
  aendern(aussage: AussageMitThemenFeld, schluessel: string[], liste: Thema[], fehler: () => void): void {
    let warteschlange = this.warteschlangen.get(aussage);
    if (!warteschlange) {
      warteschlange = this.warteschlange(aussage, fehler);
      this.warteschlangen.set(aussage, warteschlange);
    }
    aussage.themen = schluessel
      .map((s) => liste.find((t) => t.schluessel === s))
      .filter((t): t is Thema => t !== undefined);
    warteschlange.next(schluessel);
  }

  private warteschlange(aussage: AussageMitThemenFeld, fehler: () => void): Subject<string[]> {
    const auftraege = new Subject<string[]>();
    let gespeichert = aussage.themen;
    let offen = 0;
    auftraege
      .pipe(
        // Beim Einreihen zaehlen, nicht beim Senden: sonst gaelte die Aussage zwischen
        // zwei Auftraegen als fertig und zeigte kurz den vorletzten Stand.
        tap(() => offen++),
        concatMap((schluessel) =>
          this.zuordnen(aussage.statement_id, schluessel).pipe(catchError(() => of(null))),
        ),
      )
      .subscribe((themen) => {
        offen--;
        if (themen === null) {
          fehler();
        } else {
          gespeichert = themen;
        }
        if (offen === 0) {
          aussage.themen = gespeichert;
        }
      });
    return auftraege;
  }

  /** Admin: alle Aussagen zum Zuordnen, die ohne Thema zuerst. */
  aussagenZumZuordnen(): Observable<AussageMitThemen[]> {
    return this.http
      .get<AussagenMitThemenResponse>(`${this.basis}/aussagen`)
      .pipe(map((antwort) => antwort.aussagen));
  }

  /** Admin: die Zuordnungen von Hand als Testset. */
  testset(): Observable<ThemenTestsetResponse> {
    return this.http.get<ThemenTestsetResponse>(`${this.basis}/testset`);
  }
}
