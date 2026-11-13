import { Clipboard } from '@angular/cdk/clipboard';
import { Injectable, InjectionToken, inject } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';

import { ROUTES } from './constants/app.constants';

/** Rueckmeldung, wenn statt des Teilen-Menues der Link in der Zwischenablage liegt. */
export const TEILEN_LINK_KOPIERT = 'Link kopiert – füg ihn ein, wo du teilen willst.';
export const TEILEN_NICHT_KOPIERT = 'Kopieren hat nicht geklappt.';

/** Was geteilt wird: der Link, dazu ein Text, den das Teilen-Menue mitgibt. */
export interface TeilenDaten {
  url: string;
  text?: string;
  titel?: string;
}

/**
 * geteilt: Das Teilen-Menue des Geraets hat abgeschlossen. kopiert: Der Link liegt in
 * der Zwischenablage (kein Teilen-Menue). abgebrochen: Die Person hat das Menue
 * geschlossen. fehlgeschlagen: Weder Teilen noch Kopieren hat geklappt.
 */
export type TeilenErgebnis = 'geteilt' | 'kopiert' | 'abgebrochen' | 'fehlgeschlagen';

/** Der Teil von `navigator`, den das Teilen braucht; in Tests ersetzbar. */
export interface TeilenNavigator {
  share?: (daten: ShareData) => Promise<void>;
  canShare?: (daten?: ShareData) => boolean;
}

export const TEILEN_NAVIGATOR = new InjectionToken<TeilenNavigator>('TEILEN_NAVIGATOR', {
  providedIn: 'root',
  factory: () => (typeof navigator === 'undefined' ? {} : navigator),
});

/** Die Adresse einer Suche zum Teilen ("Ergebnis teilen"), wie sie die Ergebnisseite liest. */
export function sucheLink(suchtext: string, origin: string = window.location.origin): string {
  return `${origin}${ROUTES.RESULT}?searchQuery=${encodeURIComponent(suchtext)}`;
}

/** Ob wirklich geteilt oder kopiert wurde; nur dann zaehlt das Teilen einer Karte als Nutzung. */
export function hatGeteilt(ergebnis: TeilenErgebnis): boolean {
  return ergebnis === 'geteilt' || ergebnis === 'kopiert';
}

/**
 * Teilen ohne Dritte (docs/VISION.md, Teilen): mit dem Teilen-Menue des Geraets (Web
 * Share API), wo es eines gibt, sonst der Link in die Zwischenablage. Keine
 * Share-Knoepfe fremder Dienste, kein Tracking.
 *
 * Die Rueckmeldung kommt als Snackbar (MatSnackBar sagt sie ueber eine Live-Region an):
 * beim Kopieren, dass der Link bereitliegt, sonst dass es nicht geklappt hat. Nach dem
 * Teilen-Menue keine, das Menue selbst war die Rueckmeldung; nach einem Abbruch
 * (AbortError) auch keine.
 */
@Injectable({ providedIn: 'root' })
export class TeilenService {
  private clipboard = inject(Clipboard);
  private snackBar = inject(MatSnackBar);
  private nav = inject(TEILEN_NAVIGATOR);

  async teilen(daten: TeilenDaten): Promise<TeilenErgebnis> {
    const anfrage: ShareData = { url: daten.url };
    if (daten.text) {
      anfrage.text = daten.text;
    }
    if (daten.titel) {
      anfrage.title = daten.titel;
    }

    if (this.kannTeilen(anfrage)) {
      try {
        await this.nav.share!(anfrage);
        return 'geteilt';
      } catch (fehler) {
        if ((fehler as { name?: string } | null)?.name === 'AbortError') {
          return 'abgebrochen';
        }
        // NotAllowedError, DataError u. a.: dann eben kopieren.
      }
    }
    return this.kopieren(daten.url);
  }

  private kannTeilen(anfrage: ShareData): boolean {
    if (typeof this.nav.share !== 'function') {
      return false;
    }
    return typeof this.nav.canShare === 'function' ? this.nav.canShare(anfrage) : true;
  }

  private kopieren(url: string): TeilenErgebnis {
    const kopiert = this.clipboard.copy(url);
    this.snackBar.open(kopiert ? TEILEN_LINK_KOPIERT : TEILEN_NICHT_KOPIERT, 'OK', { duration: 4000 });
    return kopiert ? 'kopiert' : 'fehlgeschlagen';
  }
}
