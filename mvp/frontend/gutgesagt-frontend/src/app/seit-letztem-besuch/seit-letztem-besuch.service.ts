import { Injectable } from '@angular/core';
import { Observable, forkJoin, of } from 'rxjs';
import { catchError, map, shareReplay } from 'rxjs/operators';

import { Einwurf, EinwurfService } from '../services/einwurf.service';
import { StatementService } from '../services/statement.service';
import { UnbeantworteteAussage } from '../services/dtos/statementDtos';

/** Was der Browser vom letzten Besuch der Startseite weiss: Zeitpunkt und offene Aussagen. */
export const LETZTER_BESUCH_SCHLUESSEL = 'gutgesagt-letzter-besuch';

/** So viele Einwuerfe sieht die Startseite an; mehr Neues zaehlt sie nicht. */
const EINWUERFE_HOECHSTENS = 100;

interface Merker {
  /** ISO-Zeitpunkt des letzten Besuchs. */
  zeit: string;
  /** IDs der Aussagen, die damals in „Hier fehlt eine Antwort“ standen. */
  aussagen: string[];
}

/** Neues seit dem letzten Besuch, ohne die Nutzung (die kommt aus der Rueckmeldung). */
export interface SeitLetztemBesuch {
  einwuerfe: number;
  aussagen: number;
}

export function merkerLesen(): Merker | null {
  try {
    const roh = localStorage.getItem(LETZTER_BESUCH_SCHLUESSEL);
    if (!roh) {
      return null;
    }
    const wert: unknown = JSON.parse(roh);
    const merker = wert as Partial<Merker>;
    if (typeof merker?.zeit !== 'string' || Number.isNaN(Date.parse(merker.zeit)) || !Array.isArray(merker.aussagen)) {
      return null;
    }
    return { zeit: merker.zeit, aussagen: merker.aussagen.filter((id): id is string => typeof id === 'string') };
  } catch {
    return null;
  }
}

function merkerSchreiben(merker: Merker): void {
  try {
    localStorage.setItem(LETZTER_BESUCH_SCHLUESSEL, JSON.stringify(merker));
  } catch {
    // Ohne Speicher (privates Fenster) gibt es eben nichts „seit dem letzten Besuch“.
  }
}

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

/** Aussagen in „Hier fehlt eine Antwort“, die beim letzten Besuch noch nicht dort standen. */
export function neueAussagen(aussagen: UnbeantworteteAussage[], damals: string[]): number {
  const bekannt = new Set(damals);
  return aussagen.filter((a) => !bekannt.has(a.statement_id)).length;
}

/**
 * „Seit deinem letzten Besuch“ auf der Startseite (Nutzerfuehrung 13.11.): neue Einwuerfe
 * im Fangkorb und neue Aussagen in „Hier fehlt eine Antwort“. Nur vorhandene Abrufe, kein
 * neuer Server-Zweck: Wann der letzte Besuch war und welche Aussagen damals offen waren,
 * merkt sich allein der Browser. Beim ersten Besuch (kein Merker, privates Fenster) ist
 * nichts neu. Berechnet wird einmal je App-Start; danach bleibt der Stand stehen, bis
 * die App neu startet. Nichts verfaellt und nichts zaehlt rueckwaerts.
 */
@Injectable({ providedIn: 'root' })
export class SeitLetztemBesuchService {
  private stand$?: Observable<SeitLetztemBesuch>;

  constructor(
    private einwurfService: EinwurfService,
    private statementService: StatementService,
  ) {}

  stand(): Observable<SeitLetztemBesuch> {
    this.stand$ ??= this.berechnen().pipe(shareReplay(1));
    return this.stand$;
  }

  private berechnen(): Observable<SeitLetztemBesuch> {
    const vorher = merkerLesen();
    return forkJoin({
      einwuerfe: this.einwurfService.fangkorbLaden(1, EINWUERFE_HOECHSTENS).pipe(
        map((seite) => seite.results),
        catchError(() => of(null)),
      ),
      aussagen: this.statementService.unbeantworteteAussagen().pipe(catchError(() => of(null))),
    }).pipe(
      map(({ einwuerfe, aussagen }) => {
        merkerSchreiben({
          zeit: new Date().toISOString(),
          // Liess sich die Liste nicht laden, bleibt der alte Stand, sonst waere beim
          // naechsten Mal alles neu.
          aussagen: aussagen ? aussagen.map((a) => a.statement_id) : (vorher?.aussagen ?? []),
        });
        if (!vorher) {
          return { einwuerfe: 0, aussagen: 0 };
        }
        return {
          einwuerfe: einwuerfe ? neueEinwuerfe(einwuerfe, vorher.zeit) : 0,
          aussagen: aussagen ? neueAussagen(aussagen, vorher.aussagen) : 0,
        };
      }),
    );
  }
}
