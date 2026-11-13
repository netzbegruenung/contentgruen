import { Injectable, inject } from '@angular/core';
import { BehaviorSubject, Observable, forkJoin, of } from 'rxjs';
import { catchError, map, shareReplay } from 'rxjs/operators';

import { Einwurf, EinwurfService } from '../services/einwurf.service';
import { StatementService } from '../services/statement.service';
import { UnbeantworteteAussage } from '../services/dtos/statementDtos';
import { besuchMerkerLesen, besuchMerkerSchreiben } from './besuch-merker';
import { LETZTER_BESUCH_AN } from '../shared/geraetespeicher-schalter';

/**
 * So viele Einwuerfe sieht die Startseite an. Die neuesten kommen zuerst (eigene davor),
 * mehr Neues seit dem letzten Besuch zaehlt sie nicht.
 */
export const EINWUERFE_HOECHSTENS = 25;

/** Was die Startseite meldet, ohne die Nutzung (die kommt aus der Rueckmeldung). */
export interface SeitLetztemBesuch {
  /** Neue Einwuerfe anderer seit dem letzten Besuch, die noch Arbeit sind. */
  einwuerfe: number;
  /**
   * Wie viele Aussagen in „Hier fehlt eine Antwort“ warten; nur, wenn seitdem eine
   * dazugekommen ist, sonst 0. Die Liste traegt kein Anlagedatum, deshalb nennt die
   * Startseite die wartenden, nicht „neue“.
   */
  aussagen: number;
}

/** Ein Link, der nach dem Klick fuer diesen App-Start verschwindet. */
export type NeuesArt = 'nutzung' | 'einwuerfe' | 'aussagen';

/** Neue Einwuerfe anderer, die noch Arbeit sind (offen oder destilliert). */
export function neueEinwuerfe(einwuerfe: Einwurf[], seit: string): number {
  const grenze = Date.parse(seit);
  return einwuerfe.filter(
    (e) =>
      e.ist_eigener_einwurf !== true &&
      (e.status === 'open' || e.status === 'in_progress') &&
      Date.parse(e.created_at) > grenze,
  ).length;
}

/** Ob in „Hier fehlt eine Antwort“ eine Aussage steht, die beim letzten Besuch nicht dort stand. */
export function aussageDazu(aussagen: UnbeantworteteAussage[], damals: string[]): boolean {
  const bekannt = new Set(damals);
  return aussagen.some((a) => !bekannt.has(a.statement_id));
}

/**
 * „Seit deinem letzten Besuch“ auf der Startseite (Nutzerfuehrung 13.11.): neue Einwuerfe
 * im Fangkorb und wartende Aussagen in „Hier fehlt eine Antwort“. Nur vorhandene Abrufe
 * (je App-Start und Konto einmal Fangkorb und unbeantwortete Aussagen), kein neuer
 * Server-Zweck: Wann der letzte Besuch war und welche Aussagen damals offen waren, merkt
 * sich allein der Browser, je Konto (besuch-merker.ts). Beim ersten Besuch (kein Merker,
 * privates Fenster) ist nichts neu. Danach bleibt der Stand bis zum naechsten App-Start
 * oder Kontowechsel stehen; nichts verfaellt und nichts zaehlt rueckwaerts.
 */
@Injectable({ providedIn: 'root' })
export class SeitLetztemBesuchService {
  /** Aus bis zur Pruefung nach § 25 TDDDG: dann weder Abrufe noch Browser-Speicher. */
  private readonly aktiv = inject(LETZTER_BESUCH_AN);
  private kennung: string | null = null;
  private stand$?: Observable<SeitLetztemBesuch>;
  /** Links, die in diesem App-Start schon angeklickt wurden. */
  readonly erledigt$ = new BehaviorSubject<ReadonlySet<NeuesArt>>(new Set());

  constructor(
    private einwurfService: EinwurfService,
    private statementService: StatementService,
  ) {}

  stand(kennung: string): Observable<SeitLetztemBesuch> {
    if (!this.aktiv) {
      return of({ einwuerfe: 0, aussagen: 0 });
    }
    if (kennung !== this.kennung || !this.stand$) {
      this.kennung = kennung;
      this.erledigt$.next(new Set());
      this.stand$ = this.berechnen(kennung).pipe(shareReplay(1));
    }
    return this.stand$;
  }

  /** Nach dem Klick auf einen Link: Er verschwindet, die Sache ist gesehen. */
  erledigen(art: NeuesArt): void {
    this.erledigt$.next(new Set([...this.erledigt$.value, art]));
  }

  private berechnen(kennung: string): Observable<SeitLetztemBesuch> {
    const vorher = besuchMerkerLesen(kennung);
    return forkJoin({
      einwuerfe: this.einwurfService.fangkorbLaden(1, EINWUERFE_HOECHSTENS).pipe(
        map((seite) => seite.results),
        catchError(() => of(null)),
      ),
      aussagen: this.statementService.unbeantworteteAussagen().pipe(catchError(() => of(null))),
    }).pipe(
      map(({ einwuerfe, aussagen }) => {
        const jetzt = new Date().toISOString();
        // Was sich nicht laden liess, behaelt den alten Stand, sonst gaelte es beim
        // naechsten Mal als gesehen (Fangkorb) oder alles als neu (Aussagen).
        besuchMerkerSchreiben(kennung, {
          zeit: einwuerfe ? jetzt : (vorher?.zeit ?? jetzt),
          aussagen: aussagen ? aussagen.map((a) => a.statement_id) : (vorher?.aussagen ?? []),
        });
        if (!vorher) {
          return { einwuerfe: 0, aussagen: 0 };
        }
        return {
          einwuerfe: einwuerfe ? neueEinwuerfe(einwuerfe, vorher.zeit) : 0,
          aussagen: aussagen && aussageDazu(aussagen, vorher.aussagen) ? aussagen.length : 0,
        };
      }),
    );
  }
}
