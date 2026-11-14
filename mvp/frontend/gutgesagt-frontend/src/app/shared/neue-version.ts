import { Injectable, InjectionToken, inject } from '@angular/core';
import { Location } from '@angular/common';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NavigationError } from '@angular/router';

/**
 * Nach einem Deploy die neue Version laden, ohne dass jemand von Hand neu laden muss.
 *
 * Die Bundles tragen gehashte Namen und liegen ein Jahr im Cache, index.html gar nicht
 * (nginx.docker.conf). Nach einem Deploy fehlen die alten Chunks im neuen Container. Wer die
 * App ueber den Deploy hinweg offen hat (installierte PWA, offener Reiter) und eine noch nicht
 * geladene Route oeffnet, bekommt beim dynamischen Import eine 404. Dann hilft nur ein harter
 * Seitenwechsel auf das Ziel: Er holt die neue index.html mit den neuen Chunks.
 */

/** Meldungen der Browser und Bundler bei einem gescheiterten Chunk- bzw. Modul-Import. */
const LADEFEHLER = [
  // Chrome, Edge
  /Failed to fetch dynamically imported module/i,
  // Firefox
  /error loading dynamically imported module/i,
  // Safari
  /Importing a module script failed/i,
  // webpack (Karma, aeltere Builds)
  /Loading chunk [\w-]+ failed/i,
  /Loading CSS chunk [\w-]+ failed/i,
];

/** Innerhalb dieser Zeit nach einem automatischen Neuladen nicht noch einmal (Schleifensperre). */
export const SPERRE_MS = 10_000;

/** Schluessel im sessionStorage: Zeitpunkt des letzten automatischen Neuladens. */
export const SPERRE_SCHLUESSEL = 'gutgesagt.neueVersionGeladen';

/** Der Hinweis, wenn nicht automatisch neu geladen werden kann (Notfall). */
export const HINWEIS_TEXT = 'Gut gesagt wurde aktualisiert';
export const HINWEIS_KNOPF = 'Neu laden';

/** Harter Seitenwechsel; eigener Token, weil sich location.assign im Test nicht ersetzen laesst. */
export const SEITENWECHSEL = new InjectionToken<(url: string) => void>('Seitenwechsel', {
  providedIn: 'root',
  factory: () => (url: string) => window.location.assign(url),
});

/** Der sessionStorage, oder null, wenn schon der Zugriff scheitert (gesperrte Website-Daten). */
export const SITZUNGSSPEICHER = new InjectionToken<Storage | null>('Sitzungsspeicher', {
  providedIn: 'root',
  factory: () => {
    try {
      return window.sessionStorage;
    } catch {
      return null;
    }
  },
});

/** Was ``neueVersionLaden`` getan hat. */
export type Ausgang = 'neu-geladen' | 'hinweis' | 'laeuft-schon';

/**
 * Ist ``fehler`` ein gescheiterter Chunk- bzw. Modul-Import? Schaut auch in die Huellen, in
 * denen der Fehler ankommt: ``rejection`` (unbehandelte Promise-Ablehnung) und ``error``
 * (NavigationError).
 */
export function istLadefehler(fehler: unknown, tiefe = 0): boolean {
  if (fehler === null || fehler === undefined || tiefe > 3) return false;
  if (typeof fehler === 'string') return LADEFEHLER.some((muster) => muster.test(fehler));
  if (typeof fehler !== 'object') return false;
  const f = fehler as { name?: unknown; message?: unknown; rejection?: unknown; error?: unknown };
  if (f.name === 'ChunkLoadError') return true;
  if (typeof f.message === 'string' && LADEFEHLER.some((muster) => muster.test(f.message as string))) return true;
  return istLadefehler(f.rejection, tiefe + 1) || (f.error !== fehler && istLadefehler(f.error, tiefe + 1));
}

@Injectable({ providedIn: 'root' })
export class NeueVersionService {
  private readonly seitenwechsel = inject(SEITENWECHSEL);
  private readonly speicher = inject(SITZUNGSSPEICHER);
  private readonly snackBar = inject(MatSnackBar);
  private readonly location = inject(Location);

  /** Ein Seitenwechsel ist schon angestossen: Folgefehler derselben Seite tun nichts mehr. */
  private wechselLaeuft = false;
  private hinweisOffen = false;

  /** Fuer ``withNavigationErrorHandler``: bei einem Ladefehler hart auf das Ziel der Navigation. */
  beiNavigationsfehler(fehler: NavigationError): void {
    if (istLadefehler(fehler.error)) {
      this.neueVersionLaden(this.location.prepareExternalUrl(fehler.url));
    }
  }

  /**
   * Laedt ``zielUrl`` hart, genau einmal: Liegt das letzte automatische Neuladen keine
   * ``SPERRE_MS`` zurueck, oder laesst sich der Zeitpunkt nicht merken (kein Speicher), kommt
   * stattdessen ein Hinweis mit Knopf. So entsteht keine Schleife, falls auch die neue Version
   * ihre Chunks nicht findet.
   */
  neueVersionLaden(zielUrl: string): Ausgang {
    if (this.wechselLaeuft) return 'laeuft-schon';
    if (!this.sperreSetzen()) {
      this.hinweisZeigen(zielUrl);
      return 'hinweis';
    }
    this.wechselLaeuft = true;
    this.seitenwechsel(zielUrl);
    return 'neu-geladen';
  }

  /** Merkt den Zeitpunkt; false, wenn gesperrt oder kein Speicher da ist. */
  private sperreSetzen(): boolean {
    const jetzt = Date.now();
    try {
      if (!this.speicher) return false;
      const zuletzt = Number(this.speicher.getItem(SPERRE_SCHLUESSEL));
      if (zuletzt && jetzt - zuletzt >= 0 && jetzt - zuletzt < SPERRE_MS) return false;
      this.speicher.setItem(SPERRE_SCHLUESSEL, String(jetzt));
      // Manche Browser schlucken Schreibzugriffe still: nur weiter, wenn die Sperre wirklich steht.
      return this.speicher.getItem(SPERRE_SCHLUESSEL) === String(jetzt);
    } catch {
      return false;
    }
  }

  private hinweisZeigen(zielUrl: string): void {
    if (this.hinweisOffen) return;
    this.hinweisOffen = true;
    const hinweis = this.snackBar.open(HINWEIS_TEXT, HINWEIS_KNOPF, {
      horizontalPosition: 'center',
      verticalPosition: 'bottom',
    });
    hinweis.onAction().subscribe(() => this.seitenwechsel(zielUrl));
    hinweis.afterDismissed().subscribe(() => (this.hinweisOffen = false));
  }
}
