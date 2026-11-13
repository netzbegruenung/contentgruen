import { DestroyRef } from '@angular/core';
import { HttpContext, HttpContextToken } from '@angular/common/http';
import { EMPTY, Observable, Subscription } from 'rxjs';
import { finalize } from 'rxjs/operators';

/** So oft laden Listen nach, solange der Reiter sichtbar ist (Grundsatz 13.11.2026). */
export const NACHLADEN_MS = 30_000;

/** Nach Fehlern wartet der naechste Versuch laenger: Takt mal 1, 2, 4 (30 → 60 → 120 s). */
export const BACKOFF_STUFEN = 2;

/**
 * Markiert eine Anfrage als Hintergrund-Abfrage: Der AuthInterceptor leitet bei 401 dann
 * nicht auf /login um. Sonst risse ein Nachladen nach abgelaufener Sitzung die Person
 * mitten beim Tippen aus der Seite.
 */
export const STILLE_ABFRAGE = new HttpContextToken<boolean>(() => false);

/** HttpContext fuer eine Hintergrund-Abfrage (``STILLE_ABFRAGE``). */
export function stillerKontext(): HttpContext {
  return new HttpContext().set(STILLE_ABFRAGE, true);
}

/** Der Hinweis nach 401/403, als Link auf die Anmeldung. */
export const SITZUNG_ABGELAUFEN = 'Sitzung abgelaufen – Anmelden';

/** Nach 401/403 (Sitzung abgelaufen, keine Admin-Rechte) hilft nur neues Anmelden; Nachladen hoert auf. */
export function ohneRechte(fehler: unknown): boolean {
  const status = (fehler as { status?: unknown } | null)?.status;
  return status === 401 || status === 403;
}

/** Ergebnis eines Laufs: Daten oder der Fehler. */
export type Lauf<T> = { daten: T; fehler: null } | { daten: null; fehler: unknown };

export interface NachladeOptionen {
  /** Takt in ms; eine Funktion wird vor jedem Planen neu gefragt (etwa je nach Seite). */
  ms?: number | (() => number);
  /** Gleich beim Abonnieren laden, nicht erst beim ersten Anlass. */
  sofort?: boolean;
  /**
   * Ein Fehler, nach dem nicht weiter gefragt wird (etwa 401/403): kein Takt, kein Laden beim
   * Sichtbarwerden. Erst ein Anstoss von aussen (``anstoss$``) startet wieder.
   */
  aufhoerenBei?: (fehler: unknown) => boolean;
  /** Anstoesse von aussen, etwa nach einer Handlung: sofort laden, auch nach einem Stopp. */
  anstoss$?: Observable<unknown>;
}

function sichtbar(): boolean {
  return document.visibilityState === 'visible';
}

/**
 * Laedt ``holen`` immer wieder, solange abonniert, und meldet jeden Lauf.
 *
 * - Im Takt (``ms``), aber nur, solange der Reiter sichtbar ist; versteckt fragt niemand.
 * - Beim Sichtbarwerden sofort, danach beginnt der Takt neu.
 * - Nie zwei Laeufe zugleich: Ein Anlass waehrend eines Laufs wird danach nachgeholt.
 * - Nach Fehlern laenger warten (``BACKOFF_STUFEN``), nach einem Erfolg wieder im Takt.
 *
 * Oberflaechen laden so selbst nach; niemand muss „Aktualisieren“ druecken oder die
 * Seite neu laden.
 */
export function nachladeStrom<T>(holen: () => Observable<T>, optionen: NachladeOptionen = {}): Observable<Lauf<T>> {
  return new Observable<Lauf<T>>((abonnent) => {
    let fehlversuche = 0;
    let wecker: ReturnType<typeof setTimeout> | null = null;
    let laeuft = false;
    let nochmal = false;
    /** Abgemeldet (Teardown): endgueltig. */
    let aus = false;
    /** Nach einem Fehler laut ``aufhoerenBei``: bis zum naechsten Anstoss von aussen. */
    let gestoppt = false;
    let lauf: Subscription | null = null;

    const takt = () => (typeof optionen.ms === 'function' ? optionen.ms() : optionen.ms ?? NACHLADEN_MS);

    const planen = () => {
      if (wecker !== null) clearTimeout(wecker);
      wecker = null;
      if (aus || gestoppt) return;
      const warten = takt() * 2 ** Math.min(fehlversuche, BACKOFF_STUFEN);
      wecker = setTimeout(() => {
        wecker = null;
        // Versteckt: nichts tun, das Sichtbarwerden laedt und plant neu.
        if (sichtbar()) los();
      }, warten);
    };

    const los = () => {
      if (aus || gestoppt) return;
      if (laeuft) {
        nochmal = true;
        return;
      }
      if (wecker !== null) clearTimeout(wecker);
      wecker = null;
      laeuft = true;
      lauf = holen()
        .pipe(
          finalize(() => {
            laeuft = false;
            if (aus) return;
            if (nochmal && !gestoppt) {
              nochmal = false;
              los();
            } else {
              planen();
            }
          }),
        )
        .subscribe({
          next: (daten) => {
            fehlversuche = 0;
            abonnent.next({ daten, fehler: null });
          },
          error: (fehler) => {
            fehlversuche++;
            if (optionen.aufhoerenBei?.(fehler)) {
              gestoppt = true;
              nochmal = false;
            }
            abonnent.next({ daten: null, fehler });
          },
        });
    };

    const beiSichtbarkeit = () => {
      if (sichtbar()) {
        los();
      } else if (wecker !== null) {
        clearTimeout(wecker);
        wecker = null;
      }
    };
    document.addEventListener('visibilitychange', beiSichtbarkeit);
    const anstoss = (optionen.anstoss$ ?? EMPTY).subscribe(() => {
      gestoppt = false;
      los();
    });

    if (optionen.sofort) {
      los();
    } else {
      planen();
    }

    return () => {
      aus = true;
      if (wecker !== null) clearTimeout(wecker);
      document.removeEventListener('visibilitychange', beiSichtbarkeit);
      anstoss.unsubscribe();
      lauf?.unsubscribe();
    };
  });
}

/**
 * Laedt ``holen`` selbst nach (``nachladeStrom``, ohne sofortigen Lauf: das erste Laden
 * macht die Seite selbst), bis ``destroyRef`` endet. ``folgen`` bekommt Daten und Fehler.
 */
export function selbstNachladen<T>(
  holen: () => Observable<T>,
  destroyRef: DestroyRef,
  folgen: { next: (daten: T) => void; error?: (fehler: unknown) => void },
  takt: number | (() => number) | Omit<NachladeOptionen, 'sofort'> = NACHLADEN_MS,
): void {
  const optionen = typeof takt === 'object' ? takt : { ms: takt };
  const abo = nachladeStrom(holen, optionen).subscribe((lauf) => {
    if (lauf.fehler === null) {
      folgen.next(lauf.daten as T);
    } else {
      folgen.error?.(lauf.fehler);
    }
  });
  destroyRef.onDestroy(() => abo.unsubscribe());
}
