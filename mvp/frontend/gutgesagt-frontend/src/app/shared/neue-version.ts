import { Injectable, InjectionToken, NgZone, inject } from '@angular/core';
import { Location } from '@angular/common';
import { MatSnackBar, MatSnackBarRef, TextOnlySnackBar } from '@angular/material/snack-bar';
import { NavigationError } from '@angular/router';
import { Observable } from 'rxjs';

/**
 * Nach einem Deploy die neue Version laden, ohne dass jemand von Hand neu laden muss.
 *
 * Die Bundles tragen gehashte Namen und liegen ein Jahr im Cache, index.html gar nicht
 * (nginx.docker.conf). Nach einem Deploy fehlen die alten Chunks im neuen Container. Wer die
 * App ueber den Deploy hinweg offen hat (installierte PWA, offener Reiter) und eine noch nicht
 * geladene Route oeffnet, bekommt beim dynamischen Import eine 404. Dann hilft nur ein harter
 * Seitenwechsel auf das Ziel: Er holt die neue index.html mit den neuen Chunks.
 *
 * Schleifensperre: Vor dem Wechsel steht ein Merker (nur der Zeitpunkt) im sessionStorage; er
 * faellt nach ``SPERRE_MS``. Solange er steht, wird nicht automatisch neu geladen, nur ein Hinweis
 * gezeigt: hoechstens ein automatisches Neuladen je zehn Minuten, gleich ob ein Guard vor dem
 * Laden lange wartet oder ein ``@defer``-Block erst spaet scheitert.
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

/** So lange gilt der Merker eines automatischen Neuladens; aelter zaehlt er als abgelaufen. */
export const SPERRE_MS = 10 * 60_000;

/** So lange darf die Pruefung auf dem Server dauern; danach gilt sie als Netzfehler. */
export const PRUEFUNG_MS = 5_000;

/** Nach so langer Zeit gilt ein angestossener Wechsel als nicht passiert (etwa abgebrochen). */
export const WECHSEL_FRIST_MS = 10_000;

/** Schluessel im sessionStorage: Zeitpunkt des letzten automatischen Neuladens. */
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
  /** Die eigene index.html (no-cache): Antwortet sie, ist der Server erreichbar. */
  startseite(): string;
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
    startseite: () => new URL('index.html', document.baseURI).href,
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
  // Erst die Huellen: zone.js packt den Fehler in „Uncaught (in promise): …“ mit ``rejection``,
  // und Router wie ErrorHandler sollen denselben Kern sehen.
  for (const huelle of [f.rejection, f.error]) {
    if (huelle === fehler) continue;
    const kern = ladefehlerKern(huelle, tiefe + 1);
    if (kern !== null) return kern;
  }
  return typeof f.message === 'string' && ladefehlerKern(f.message) !== null ? fehler : null;
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
  private readonly zone = inject(NgZone);

  /** Eine Pruefung oder ein Wechsel laeuft: Folgefehler derselben Seite tun nichts mehr. */
  private laeuft = false;
  /** Schon behandelte Fehler: Router und ErrorHandler melden denselben Fehler nacheinander. */
  private readonly behandelt = new WeakSet<object>();
  private hinweis: { ziel: string; ref: MatSnackBarRef<TextOnlySnackBar> } | null = null;

  /**
   * Beim Start: Ein abgelaufener Merker faellt gleich, ein stehender, sobald er abgelaufen ist.
   * So liegt er nicht laenger als ``SPERRE_MS`` im Browser, auch wenn kein Fehler mehr kommt.
   */
  aufraeumen(): void {
    const zeitpunkt = this.sperreZeitpunkt();
    if (zeitpunkt === null) return;
    // Ausserhalb der Zone: Ein Wecker ueber zehn Minuten soll die App nicht als unruhig fuehren.
    this.zone.runOutsideAngular(() => setTimeout(() => this.sperreZeitpunkt(), zeitpunkt + SPERRE_MS - Date.now()));
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
   * fehlende Skript antwortet mit 404 (nennt die Meldung keins, wie Safari und ``@defer``: die
   * eigene index.html antwortet). Steht der Merker eines frueheren automatischen Neuladens noch
   * oder laesst er sich nicht setzen (kein Speicher), kommt stattdessen ein Hinweis mit Knopf.
   */
  async neueVersionLaden(zielUrl: string, fehler?: unknown): Promise<Ausgang> {
    const kern = ladefehlerKern(fehler);
    if (kern !== null && typeof kern === 'object') {
      if (this.behandelt.has(kern)) return 'schon-behandelt';
      this.behandelt.add(kern);
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
      const neueVersion = chunk !== null ? await this.fehltAufDemServer(chunk) : await this.serverErreichbar();
      if (!neueVersion) {
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
    const status = await this.kopfStatus(chunk);
    return status === 404 || status === 410;
  }

  /** Ohne Adresse des Chunks: Antwortet die eigene index.html mit 2xx, ist es kein Netzproblem. */
  private async serverErreichbar(): Promise<boolean> {
    const status = await this.kopfStatus(this.browser.startseite());
    return status !== null && status >= 200 && status < 300;
  }

  /**
   * HEAD ohne Cache, abgebrochen nach ``PRUEFUNG_MS``; null bei Netzfehler oder Zeitueberschreitung.
   * AbortController und eigener Wecker statt ``AbortSignal.timeout``: Der Wecker beendet die
   * Pruefung auch, wenn ``fetch`` das Signal nicht beachtet.
   */
  private async kopfStatus(url: string): Promise<number | null> {
    const abbruch = new AbortController();
    let wecker: ReturnType<typeof setTimeout> | undefined;
    const zuSpaet = new Promise<null>((fertig) => {
      wecker = setTimeout(() => {
        abbruch.abort();
        fertig(null);
      }, PRUEFUNG_MS);
    });
    try {
      const antwort = this.browser
        .abrufen(url, { method: 'HEAD', cache: 'no-store', signal: abbruch.signal })
        .then((a) => a.status);
      return await Promise.race([antwort, zuSpaet]);
    } catch {
      return null;
    } finally {
      clearTimeout(wecker);
    }
  }

  /**
   * Der Zeitpunkt eines geltenden Merkers, oder null. Ein Merker aelter als ``SPERRE_MS``, aus
   * der Zukunft oder unlesbar zaehlt als abgelaufen und faellt weg.
   */
  private sperreZeitpunkt(): number | null {
    try {
      const speicher = this.browser.speicher();
      const wert = speicher?.getItem(SPERRE_SCHLUESSEL) ?? null;
      if (wert === null) return null;
      const zeitpunkt = Number(wert);
      const alter = Date.now() - zeitpunkt;
      if (Number.isFinite(zeitpunkt) && alter >= 0 && alter < SPERRE_MS) return zeitpunkt;
      speicher!.removeItem(SPERRE_SCHLUESSEL);
      return null;
    } catch {
      return null;
    }
  }

  /** Setzt den Merker; false, wenn ein geltender schon steht oder kein Speicher da ist. */
  private sperreSetzen(): boolean {
    const jetzt = String(Date.now());
    try {
      const speicher = this.browser.speicher();
      if (!speicher || this.sperreZeitpunkt() !== null) return false;
      speicher.setItem(SPERRE_SCHLUESSEL, jetzt);
      // Manche Browser schlucken Schreibzugriffe still: nur weiter, wenn der Merker wirklich steht.
      return speicher.getItem(SPERRE_SCHLUESSEL) === jetzt;
    } catch {
      return false;
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
        // Danach erneut schauen: Vielleicht wartet schon die naechste fremde Snackbar.
        (andere.afterDismissed as () => Observable<unknown>)().subscribe(() => this.nachVerdraengung(ref, wieder));
      }
    } catch {
      // Still: ohne Zugriff auf die offene Snackbar kein Wiederkommen.
    }
  }
}
