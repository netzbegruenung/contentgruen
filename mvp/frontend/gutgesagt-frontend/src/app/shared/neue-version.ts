import { Injectable, InjectionToken, Injector, inject } from '@angular/core';
import { Location } from '@angular/common';
import { MatSnackBar, MatSnackBarRef, TextOnlySnackBar } from '@angular/material/snack-bar';
import { NavigationEnd, NavigationError, Router } from '@angular/router';
import { Observable } from 'rxjs';
import { filter, take } from 'rxjs/operators';

/**
 * Nach einem Deploy die neue Version laden, ohne dass jemand von Hand neu laden muss.
 *
 * Die Bundles tragen gehashte Namen und liegen ein Jahr im Cache, index.html gar nicht
 * (nginx.docker.conf). Nach einem Deploy fehlen die alten Chunks im neuen Container. Wer die
 * App ueber den Deploy hinweg offen hat (installierte PWA, offener Reiter) und eine noch nicht
 * geladene Route oeffnet, bekommt beim dynamischen Import eine 404. Dann hilft nur ein harter
 * Seitenwechsel auf das Ziel: Er holt die neue index.html mit den neuen Chunks.
 *
 * Schleifensperre: Vor dem Wechsel steht ein Merker im sessionStorage. Er faellt erst, wenn die
 * neu geladene Seite ihre erste Navigation geschafft hat und danach ``BESTAETIGT_MS`` ohne
 * Ladefehler lief. Solange er steht, wird nicht automatisch neu geladen, nur ein Hinweis gezeigt.
 * So bleibt es bei einem Wechsel, auch wenn die neue Version selbst ihre Chunks nicht findet
 * oder ein Guard vor dem Laden lange auf den Server wartet.
 */

/** Meldungen der Browser bei einem gescheiterten dynamischen Import (der Builder ist esbuild). */
const LADEFEHLER = [
  // Chrome, Edge
  /Failed to fetch dynamically imported module/i,
  // Firefox
  /error loading dynamically imported module/i,
  // Safari
  /Importing a module script failed/i,
];

/** ``@defer`` ohne ``@error``-Block: Angular meldet nur NG0750, ohne die Ursache. */
const DEFER_FEHLER_CODE = -750;
const DEFER_FEHLER = /^NG0?750\b/;

/** So lange muss die neu geladene Seite nach ihrer ersten Navigation fehlerfrei laufen. */
export const BESTAETIGT_MS = 30_000;

/** Nach so langer Zeit gilt ein angestossener Wechsel als nicht passiert (etwa abgebrochen). */
export const WECHSEL_FRIST_MS = 5_000;

/** Schluessel im sessionStorage: Zeitpunkt des automatischen Neuladens, bis es bestaetigt ist. */
export const SPERRE_SCHLUESSEL = 'gutgesagt.neueVersionGeladen';

/** Der Hinweis, wenn nicht automatisch neu geladen wird (Notfall). */
export const HINWEIS_TEXT = 'Gut gesagt wurde aktualisiert';
export const HINWEIS_KNOPF = 'Neu laden';

/** Kein Netz: Dann fehlt keine neue Version, sondern die Verbindung. */
export const OFFLINE_TEXT = 'Keine Internetverbindung. Bitte überprüfe deine Verbindung.';
/** Der Chunk ist da oder der Server antwortet nicht sauber: ein Netzproblem, kein Deploy. */
export const NETZFEHLER_TEXT = 'Die Seite konnte nicht geladen werden. Bitte versuche es gleich noch einmal.';

/** Der Ausschnitt von ``window.location``, den ``hartWechseln`` braucht. */
export interface Ort {
  readonly href: string;
  readonly pathname: string;
  readonly search: string;
  assign(url: string): void;
  reload(): void;
}

/** Der Ausschnitt von ``window.history``, den ``hartWechseln`` braucht. */
export interface Verlauf {
  readonly state: unknown;
  replaceState(state: unknown, unused: string, url: string): void;
}

/**
 * Laedt ``url`` hart. Gleicher Pfad und gleiche Query: ``location.assign`` waere dann nur ein
 * Sprung im Dokument (mit Fragment) oder gar nichts; deshalb Adresse ersetzen und neu laden.
 */
export function hartWechseln(url: string, ort: Ort, verlauf: Verlauf): void {
  const ziel = new URL(url, ort.href);
  const aktuell = new URL(ort.href);
  if (ziel.origin === aktuell.origin && ziel.pathname === ort.pathname && ziel.search === ort.search) {
    verlauf.replaceState(verlauf.state, '', ziel.href);
    ort.reload();
  } else {
    ort.assign(ziel.href);
  }
}

/** Was der Browser bereitstellt; eigener Token, weil sich location & Co. im Test nicht ersetzen lassen. */
export interface Browser {
  wechseln(url: string): void;
  /** Die aktuelle Adresse (window.location.href). */
  adresse(): string;
  /** Der sessionStorage, oder null, wenn schon der Zugriff scheitert (gesperrte Website-Daten). */
  speicher(): Storage | null;
  online(): boolean;
  abrufen(url: string, init: RequestInit): Promise<Response>;
}

export const BROWSER = new InjectionToken<Browser>('Browser', {
  providedIn: 'root',
  factory: () => ({
    wechseln: (url) => hartWechseln(url, window.location, window.history),
    adresse: () => window.location.href,
    speicher: () => {
      try {
        return window.sessionStorage;
      } catch {
        return null;
      }
    },
    online: () => navigator.onLine,
    abrufen: (url, init) => fetch(url, init),
  }),
});

/** Was ``neueVersionLaden`` getan hat. */
export type Ausgang = 'neu-geladen' | 'hinweis' | 'netzfehler' | 'laeuft-schon' | 'schon-behandelt';

/**
 * Der gescheiterte Import in ``fehler``, oder null. Schaut auch in die Huellen, in denen er
 * ankommt: ``rejection`` (unbehandelte Promise-Ablehnung) und ``error`` (NavigationError).
 */
export function ladefehlerKern(fehler: unknown, tiefe = 0): object | string | null {
  if (fehler === null || fehler === undefined || tiefe > 3) return null;
  if (typeof fehler === 'string') {
    return LADEFEHLER.some((muster) => muster.test(fehler)) || DEFER_FEHLER.test(fehler) ? fehler : null;
  }
  if (typeof fehler !== 'object') return null;
  const f = fehler as { code?: unknown; message?: unknown; rejection?: unknown; error?: unknown };
  if (f.code === DEFER_FEHLER_CODE) return fehler;
  if (typeof f.message === 'string' && ladefehlerKern(f.message) !== null) return fehler;
  for (const huelle of [f.rejection, f.error]) {
    if (huelle === fehler) continue;
    const kern = ladefehlerKern(huelle, tiefe + 1);
    if (kern !== null) return kern;
  }
  return null;
}

/** Ist ``fehler`` ein gescheiterter Chunk- bzw. Modul-Import (auch ``@defer``)? */
export function istLadefehler(fehler: unknown): boolean {
  return ladefehlerKern(fehler) !== null;
}

/** Die Adresse des fehlenden Skripts aus der Meldung (Chrome, Firefox nennen sie, Safari nicht). */
export function chunkAdresse(fehler: unknown, basis: string): string | null {
  const kern = ladefehlerKern(fehler);
  const text = typeof kern === 'string' ? kern : (kern as { message?: unknown } | null)?.message;
  if (typeof text !== 'string') return null;
  const treffer = /(https?:\/\/[^\s'"]+?\.m?js)(?=[\s'"?#]|$)/.exec(text);
  if (!treffer) return null;
  try {
    const adresse = new URL(treffer[1]);
    // Nur eigene Skripte pruefen; fremde Adressen fragt die App nicht ab.
    return adresse.origin === new URL(basis).origin ? adresse.href : null;
  } catch {
    return null;
  }
}

@Injectable({ providedIn: 'root' })
export class NeueVersionService {
  private readonly browser = inject(BROWSER);
  private readonly snackBar = inject(MatSnackBar);
  private readonly location = inject(Location);
  // Spaet geholt: Der globale ErrorHandler braucht diesen Dienst, der Router ihn womoeglich.
  private readonly injector = inject(Injector);

  /** Eine Pruefung oder ein Wechsel laeuft: Folgefehler derselben Seite tun nichts mehr. */
  private laeuft = false;
  /** Schon behandelte Fehler: Router und ErrorHandler melden denselben Fehler nacheinander. */
  private readonly behandelt = new WeakSet<object>();
  private hinweis: { ziel: string; ref: MatSnackBarRef<TextOnlySnackBar> } | null = null;
  private bestaetigung: ReturnType<typeof setTimeout> | null = null;

  /** Beim Start: Nach der ersten geschafften Navigation und ``BESTAETIGT_MS`` Ruhe faellt der Merker. */
  beobachten(): void {
    this.injector.get(Router).events
      .pipe(
        filter((ereignis) => ereignis instanceof NavigationEnd),
        take(1),
      )
      .subscribe(() => {
        this.bestaetigung = setTimeout(() => {
          this.bestaetigung = null;
          this.sperreLoeschen();
        }, BESTAETIGT_MS);
      });
  }

  /** Fuer ``withNavigationErrorHandler``: bei einem Ladefehler hart auf das Ziel der Navigation. */
  beiNavigationsfehler(fehler: NavigationError): void {
    if (istLadefehler(fehler.error)) {
      void this.neueVersionLaden(this.location.prepareExternalUrl(fehler.url), fehler.error);
    }
  }

  /** Fuer den globalen ErrorHandler (etwa ``@defer``): die aktuelle Adresse neu laden. */
  beiFehler(fehler: unknown): void {
    void this.neueVersionLaden(this.browser.adresse(), fehler);
  }

  /**
   * Laedt ``zielUrl`` hart, wenn wirklich eine neue Version da ist: nicht offline, und das
   * fehlende Skript (sofern die Meldung es nennt) antwortet mit 404. Steht der Merker eines
   * frueheren automatischen Neuladens noch oder laesst er sich nicht setzen (kein Speicher),
   * kommt stattdessen ein Hinweis mit Knopf.
   */
  async neueVersionLaden(zielUrl: string, fehler?: unknown): Promise<Ausgang> {
    const kern = ladefehlerKern(fehler);
    if (kern !== null && typeof kern === 'object') {
      if (this.behandelt.has(kern)) return 'schon-behandelt';
      this.behandelt.add(kern);
    }
    // Ein Fehler, waehrend die neu geladene Seite noch nicht bestaetigt ist: Merker bleibt.
    if (this.bestaetigung !== null) {
      clearTimeout(this.bestaetigung);
      this.bestaetigung = null;
    }
    if (this.laeuft) return 'laeuft-schon';
    this.laeuft = true;
    let gewechselt = false;
    try {
      if (!this.browser.online()) {
        this.meldung(OFFLINE_TEXT);
        return 'netzfehler';
      }
      const chunk = chunkAdresse(fehler, this.browser.adresse());
      if (chunk !== null && !(await this.fehltAufDemServer(chunk))) {
        this.meldung(NETZFEHLER_TEXT);
        return 'netzfehler';
      }
      if (!this.sperreSetzen()) {
        this.hinweisZeigen(zielUrl);
        return 'hinweis';
      }
      gewechselt = true;
      this.browser.wechseln(zielUrl);
      // Bleibt die Seite stehen (Wechsel abgebrochen), darf ein spaeterer Fehler es neu versuchen.
      setTimeout(() => (this.laeuft = false), WECHSEL_FRIST_MS);
      return 'neu-geladen';
    } finally {
      if (!gewechselt) this.laeuft = false;
    }
  }

  /** Nur ein 404 (oder 410) heisst: Diese Version gibt es nicht mehr. Netzfehler und 5xx nicht. */
  private async fehltAufDemServer(chunk: string): Promise<boolean> {
    try {
      const antwort = await this.browser.abrufen(chunk, { method: 'HEAD', cache: 'no-store' });
      return antwort.status === 404 || antwort.status === 410;
    } catch {
      return false;
    }
  }

  /** Setzt den Merker; false, wenn er schon steht oder kein Speicher da ist. */
  private sperreSetzen(): boolean {
    const jetzt = String(Date.now());
    try {
      const speicher = this.browser.speicher();
      if (!speicher || speicher.getItem(SPERRE_SCHLUESSEL) !== null) return false;
      speicher.setItem(SPERRE_SCHLUESSEL, jetzt);
      // Manche Browser schlucken Schreibzugriffe still: nur weiter, wenn der Merker wirklich steht.
      return speicher.getItem(SPERRE_SCHLUESSEL) === jetzt;
    } catch {
      return false;
    }
  }

  private sperreLoeschen(): void {
    try {
      this.browser.speicher()?.removeItem(SPERRE_SCHLUESSEL);
    } catch {
      // Ohne Speicher gibt es auch keinen Merker.
    }
  }

  private meldung(text: string): void {
    this.snackBar.open(text, 'Schließen', {
      duration: 5000,
      horizontalPosition: 'center',
      verticalPosition: 'bottom',
      panelClass: ['error-snackbar'],
    });
  }

  /**
   * Der Hinweis bleibt stehen, bis jemand „Neu laden“ drueckt. Verdraengt ihn eine andere
   * Snackbar, kommt er zurueck, sobald diese geschlossen ist.
   */
  private hinweisZeigen(zielUrl: string): void {
    if (this.hinweis !== null) {
      this.hinweis.ziel = zielUrl;
      return;
    }
    const ref = this.snackBar.open(HINWEIS_TEXT, HINWEIS_KNOPF, {
      horizontalPosition: 'center',
      verticalPosition: 'bottom',
    });
    const hinweis = { ziel: zielUrl, ref };
    this.hinweis = hinweis;
    ref.onAction().subscribe(() => this.browser.wechseln(hinweis.ziel));
    ref.afterDismissed().subscribe(({ dismissedByAction } = { dismissedByAction: false }) => {
      this.hinweis = null;
      if (dismissedByAction) return;
      this.nachVerdraengung(ref, () => this.hinweisZeigen(hinweis.ziel));
    });
  }

  /**
   * Ruft ``wieder`` auf, sobald die Snackbar geschlossen ist, die ``ref`` verdraengt hat.
   * ``_openedSnackBarRef`` ist ein oeffentlicher Getter mit Unterstrich in Angular Material:
   * Faellt er bei einem Update weg oder aendert sich seine Form, kommt der Hinweis eben nicht
   * zurueck; geworfen wird nichts, und eine fremde Snackbar wird nicht sofort ersetzt.
   */
  private nachVerdraengung(ref: MatSnackBarRef<TextOnlySnackBar>, wieder: () => void): void {
    try {
      const snackBar = this.snackBar as unknown as Record<string, unknown>;
      if (!('_openedSnackBarRef' in snackBar)) return;
      const andere = snackBar['_openedSnackBarRef'] as { afterDismissed?: unknown } | null | undefined;
      if (andere === null) {
        // Nichts verdraengt ihn (etwa dismiss() von aussen): gleich wieder zeigen.
        wieder();
      } else if (andere !== ref && typeof andere?.afterDismissed === 'function') {
        (andere.afterDismissed as () => Observable<unknown>)().subscribe(() => wieder());
      }
    } catch {
      // Still: ohne Zugriff auf die offene Snackbar kein Wiederkommen.
    }
  }
}
