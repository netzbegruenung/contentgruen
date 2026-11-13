import { Injectable } from '@angular/core';
import { Observable, Subject, merge, of } from 'rxjs';
import { catchError, map, scan, shareReplay, switchMap } from 'rxjs/operators';

import { ModerationService } from './moderation.service';
import { nachladeAnlaesse } from '../shared/selbst-nachladen';

/** So viele offene Meldungen fragt die Zahl hoechstens ab (Grenze des Endpunkts). */
export const MELDUNGEN_GRENZE = 100;

/** Offene Meldungen: wie viele und seit wann die aelteste wartet. */
export interface OffeneMeldungen {
  anzahl: number;
  /** Die Grenze ist erreicht: Es koennen mehr sein, und die aelteste kann fehlen. */
  mehr: boolean;
  /** Zeitpunkt der aeltesten offenen Meldung, ohne offene null. */
  aelteste: string | null;
}

/** Offene Loeschauftraege und wie viele davon ueberfaellig sind. */
export interface OffeneLoeschauftraege {
  anzahl: number;
  ueberfaellig: number;
}

/**
 * Der Stand einer Abfrage: ``daten`` null heisst noch nie geladen. Scheitert ein
 * Nachladen, bleiben die letzten Daten stehen und ``fehler`` ist gesetzt, bis der
 * naechste Versuch klappt.
 */
export interface Stand<T> {
  daten: T | null;
  fehler: boolean;
}

/**
 * Was im Admin-Bereich zu tun ist, fuer die Zahl am Admin-Link und die Zeile „Zu tun“.
 *
 * Laedt selbst nach (``nachladeAnlaesse``), solange jemand zuhoert, und teilt das
 * Ergebnis: Kopf und Zeile fragen nicht doppelt. Ohne Abonnent fragt niemand; die
 * Zahl abonniert nur, wer Admin ist. Nach einer Handlung (Abweisen, Sperren,
 * Loeschablauf) stoesst ``aktualisieren`` sofort an.
 */
@Injectable({ providedIn: 'root' })
export class ZuTunService {
  private readonly anstoss$ = new Subject<void>();

  readonly meldungen$: Observable<Stand<OffeneMeldungen>>;
  readonly loeschauftraege$: Observable<Stand<OffeneLoeschauftraege>>;

  constructor(moderation: ModerationService) {
    this.meldungen$ = this.abfragen(() =>
      moderation.getReports('pending', MELDUNGEN_GRENZE).pipe(
        map((antwort) => ({
          anzahl: antwort.reports.length,
          mehr: antwort.reports.length >= MELDUNGEN_GRENZE,
          aelteste: aeltester(antwort.reports.map((meldung) => meldung.created)),
        })),
      ),
    );
    this.loeschauftraege$ = this.abfragen(() =>
      moderation.getLoeschauftraege().pipe(
        map((antwort) => ({
          anzahl: antwort.auftraege.length,
          ueberfaellig: antwort.auftraege.filter((auftrag) => auftrag.ueberfaellig).length,
        })),
      ),
    );
  }

  /** Sofort neu fragen, etwa nach dem Abweisen einer Meldung. */
  aktualisieren(): void {
    this.anstoss$.next();
  }

  private abfragen<T>(holen: () => Observable<T>): Observable<Stand<T>> {
    return merge(of(undefined), nachladeAnlaesse(), this.anstoss$).pipe(
      switchMap(() =>
        holen().pipe(
          map((daten): Stand<T> => ({ daten, fehler: false })),
          catchError(() => of<Stand<T>>({ daten: null, fehler: true })),
        ),
      ),
      scan((vorher: Stand<T>, jetzt: Stand<T>) => (jetzt.fehler ? { daten: vorher.daten, fehler: true } : jetzt), {
        daten: null,
        fehler: false,
      } as Stand<T>),
      shareReplay({ bufferSize: 1, refCount: true }),
    );
  }
}

/** Der frueheste lesbare Zeitpunkt; unlesbare zaehlen nicht. */
function aeltester(zeitpunkte: string[]): string | null {
  let frueheste: string | null = null;
  let millis = Infinity;
  for (const zeitpunkt of zeitpunkte) {
    const wert = new Date(zeitpunkt).getTime();
    if (!Number.isNaN(wert) && wert < millis) {
      millis = wert;
      frueheste = zeitpunkt;
    }
  }
  return frueheste;
}

/**
 * Wie lange etwas schon wartet, fuer „älteste seit …“: unter einer Stunde, in Stunden
 * bis zwei Tage, danach in Tagen.
 */
export function wartetSeit(zeitpunkt: string, jetzt: Date = new Date()): string {
  const stunden = Math.floor((jetzt.getTime() - new Date(zeitpunkt).getTime()) / 3_600_000);
  if (!(stunden >= 1)) {
    return 'seit unter einer Stunde';
  }
  if (stunden < 48) {
    return stunden === 1 ? 'seit 1 Stunde' : `seit ${stunden} Stunden`;
  }
  return `seit ${Math.floor(stunden / 24)} Tagen`;
}
