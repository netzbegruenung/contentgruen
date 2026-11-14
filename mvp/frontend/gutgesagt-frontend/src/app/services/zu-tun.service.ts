import { Injectable } from '@angular/core';
import { EMPTY, Observable, Subject, merge } from 'rxjs';
import { map, scan, shareReplay } from 'rxjs/operators';

import { ContentReport, LoeschauftraegeResponse, ModerationService } from './moderation.service';
import { SuchanfragenFreigabeService } from './suchanfragen-freigabe.service';
import { NACHLADEN_MS, nachladeStrom, ohneRechte } from '../shared/selbst-nachladen';

/** So viele offene Meldungen fragt die Zahl hoechstens ab (Grenze des Endpunkts). */
export const MELDUNGEN_GRENZE = 100;

/** Takt der Zahl am Admin-Link ausserhalb des Admin-Bereichs; im Admin-Bereich NACHLADEN_MS. */
export const KOPF_NACHLADEN_MS = 120_000;

/** Im Admin-Bereich alle 30 s, sonst alle 120 s: Die Zahl im Kopf soll nicht jede Seite belasten. */
export function zuTunTakt(): number {
  return window.location.pathname.startsWith('/admin') ? NACHLADEN_MS : KOPF_NACHLADEN_MS;
}

/** Nach 401/403 fragt niemand weiter, bis ein Anstoss (``aktualisieren``) oder die naechste Anmeldung kommt. */
export { ohneRechte };

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

/** Suchanfragen, die auf Freigabe warten (Vormoderation, #664). */
export interface WartendeSuchanfragen {
  anzahl: number;
}

/** „1 Suchanfrage wartet auf Freigabe“ / „N Suchanfragen warten auf Freigabe“ (freigegeben 14.11.2026). */
export function suchanfragenText(anzahl: number): string {
  return anzahl === 1 ? '1 Suchanfrage wartet auf Freigabe' : `${anzahl} Suchanfragen warten auf Freigabe`;
}

/** Leerfall in „Zu tun“ (freigegeben 14.11.2026). */
export const KEINE_SUCHANFRAGEN = 'Keine Suchanfragen zur Freigabe';

/**
 * Der Stand einer Abfrage: ``daten`` null heisst noch nie geladen. Scheitert ein
 * Nachladen, bleiben die letzten Daten stehen und ``fehler`` ist gesetzt, bis der
 * naechste Versuch klappt.
 */
export interface Stand<T> {
  daten: T | null;
  fehler: boolean;
  /** Der letzte Fehler war 401/403: Es wird nicht weiter gefragt, anmelden hilft. */
  abgelaufen?: boolean;
}

function standAus<T>(lauf: { daten: T | null; fehler: unknown }): Stand<T> {
  return lauf.fehler === null
    ? { daten: lauf.daten, fehler: false }
    : { daten: null, fehler: true, ...(ohneRechte(lauf.fehler) ? { abgelaufen: true } : {}) };
}

/** Offene Meldungen aus einer Liste offener Meldungen, wie der Endpunkt sie liefert. */
export function offeneMeldungen(meldungen: ContentReport[]): OffeneMeldungen {
  return {
    anzahl: meldungen.length,
    mehr: meldungen.length >= MELDUNGEN_GRENZE,
    aelteste: aeltester(meldungen.map((meldung) => meldung.created)),
  };
}

function letzterStand<T>(vorher: Stand<T>, jetzt: Stand<T>): Stand<T> {
  return jetzt.fehler ? { ...jetzt, daten: vorher.daten } : jetzt;
}

/**
 * Was im Admin-Bereich zu tun ist, fuer die Zahl am Admin-Link, die Zeile „Zu tun“, die
 * Zahlen an den Umschaltern der Moderation und die Liste der Loeschauftraege. Dazu die
 * Suchanfragen, die auf Freigabe warten (#664): nur ihre Zahl, die Liste laedt die Ansicht.
 *
 * Laedt selbst nach (``nachladeStrom``), solange jemand zuhoert, und teilt das Ergebnis:
 * Kopf, Zeile und Moderation fragen nicht doppelt. Ohne Abonnent fragt niemand; die
 * Zahl abonniert nur, wer Admin ist. Alle Abfragen sind still (kein Sprung auf /login),
 * nach 401/403 hoert sie auf. Zeigt die Moderation die offenen Meldungen ohnehin, speist
 * sie den Dienst (``meldungenGespeist``), und er fragt solange nicht selbst.
 */
@Injectable({ providedIn: 'root' })
export class ZuTunService {
  private readonly anstoss$ = new Subject<void>();
  private readonly gespeist$ = new Subject<OffeneMeldungen>();
  /** Bis wann die Moderation die offenen Meldungen liefert (ms seit Epoche). */
  private gespeistBis = 0;

  readonly meldungen$: Observable<Stand<OffeneMeldungen>>;
  /** Die offenen Loeschauftraege selbst, fuer deren Liste in der Moderation. */
  readonly loeschauftraegeAntwort$: Observable<Stand<LoeschauftraegeResponse>>;
  readonly loeschauftraege$: Observable<Stand<OffeneLoeschauftraege>>;
  readonly suchanfragen$: Observable<Stand<WartendeSuchanfragen>>;

  constructor(moderation: ModerationService, suchanfragen: SuchanfragenFreigabeService) {
    const optionen = { sofort: true, ms: zuTunTakt, aufhoerenBei: ohneRechte, anstoss$: this.anstoss$ };

    this.meldungen$ = merge(
      nachladeStrom(
        () =>
          Date.now() < this.gespeistBis
            ? EMPTY
            : moderation.getReports('pending', MELDUNGEN_GRENZE, 0, true).pipe(map((antwort) => offeneMeldungen(antwort.reports))),
        optionen,
      ).pipe(map((lauf) => standAus<OffeneMeldungen>(lauf))),
      this.gespeist$.pipe(map((daten): Stand<OffeneMeldungen> => ({ daten, fehler: false }))),
    ).pipe(
      scan(letzterStand<OffeneMeldungen>, { daten: null, fehler: false } as Stand<OffeneMeldungen>),
      shareReplay({ bufferSize: 1, refCount: true }),
    );

    this.loeschauftraegeAntwort$ = nachladeStrom(() => moderation.getLoeschauftraege(true), optionen).pipe(
      map((lauf) => standAus<LoeschauftraegeResponse>(lauf)),
      scan(letzterStand<LoeschauftraegeResponse>, { daten: null, fehler: false } as Stand<LoeschauftraegeResponse>),
      shareReplay({ bufferSize: 1, refCount: true }),
    );

    this.suchanfragen$ = nachladeStrom(() => suchanfragen.anzahl(true), optionen).pipe(
      map((lauf) => standAus<WartendeSuchanfragen>(lauf)),
      scan(letzterStand<WartendeSuchanfragen>, { daten: null, fehler: false } as Stand<WartendeSuchanfragen>),
      shareReplay({ bufferSize: 1, refCount: true }),
    );

    this.loeschauftraege$ = this.loeschauftraegeAntwort$.pipe(
      map((stand) => ({
        daten: stand.daten
          ? {
              anzahl: stand.daten.auftraege.length,
              ueberfaellig: stand.daten.auftraege.filter((auftrag) => auftrag.ueberfaellig).length,
            }
          : null,
        fehler: stand.fehler,
        ...(stand.abgelaufen ? { abgelaufen: true } : {}),
      })),
    );
  }

  /** Sofort neu fragen, etwa nach dem Abweisen einer Meldung, einem Loeschablauf oder einer Freigabe. */
  aktualisieren(): void {
    this.gespeistBis = 0;
    this.anstoss$.next();
  }

  /**
   * Die Moderation hat die offenen Meldungen gerade geladen: Sie gelten als Stand, und der
   * Dienst fragt bis kurz nach ihrem naechsten Nachladen nicht selbst.
   */
  meldungenGespeist(meldungen: ContentReport[]): void {
    this.gespeistBis = Date.now() + NACHLADEN_MS + 5_000;
    this.gespeist$.next(offeneMeldungen(meldungen));
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
