import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

/** Ein Link, der nach dem Klick fuer diesen App-Start verschwindet. */
export type NeuesArt = 'nutzung' | 'einwuerfe' | 'aussagen';

/**
 * Vorgaenger-Staende im Browser aus der Entwicklung von #672; nie in einem Release, aber
 * auf Test-Stacks moeglich. Sie werden einmal entfernt, gelesen wird nichts mehr.
 */
const ALTE_MERKER = 'gutgesagt-letzter-besuch';

/** Entfernt die alten Browser-Merker; ohne Speicher passiert nichts. */
export function alteBesuchMerkerEntfernen(): void {
  try {
    const schluessel: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const name = localStorage.key(i);
      if (name?.startsWith(ALTE_MERKER)) {
        schluessel.push(name);
      }
    }
    schluessel.forEach((name) => localStorage.removeItem(name));
  } catch {
    // Ohne Speicher gibt es nichts aufzuraeumen.
  }
}

/**
 * „Seit deinem letzten Besuch“ auf der Startseite (Nutzerfuehrung 13.11.): Die Zahlen
 * kommen alle vom Server, aus der Antwort des Besuchs beim App-Start (Zaehlerstaende am
 * Konto, kein Zeitpunkt, kein Browser-Speicher). Hier steht nur, welche Links in diesem
 * App-Start schon angeklickt wurden; beim Kontowechsel faengt das neu an.
 */
@Injectable({ providedIn: 'root' })
export class SeitLetztemBesuchService {
  private kennung: string | null = null;
  readonly erledigt$ = new BehaviorSubject<ReadonlySet<NeuesArt>>(new Set());
  private aufgeraeumt = false;

  /** Einmal je App-Start die alten Merker entfernen; bei neuer Kennung die Klicks vergessen. */
  fuer(kennung: string): void {
    if (!this.aufgeraeumt) {
      this.aufgeraeumt = true;
      alteBesuchMerkerEntfernen();
    }
    if (kennung !== this.kennung) {
      this.kennung = kennung;
      this.erledigt$.next(new Set());
    }
  }

  /** Nach dem Klick auf einen Link: Er verschwindet, die Sache ist gesehen. */
  erledigen(art: NeuesArt): void {
    this.erledigt$.next(new Set([...this.erledigt$.value, art]));
  }
}
