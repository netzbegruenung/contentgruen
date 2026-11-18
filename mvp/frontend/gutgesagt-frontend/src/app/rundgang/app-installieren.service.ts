import { DOCUMENT } from '@angular/common';
import { DestroyRef, Injectable, InjectionToken, inject, signal } from '@angular/core';
import { Subject } from 'rxjs';
import { geraetAusBrowser } from './home-bildschirm';

/**
 * Das Ereignis `beforeinstallprompt` von Chrome und Edge (Android und Computer). Es steht
 * nicht in den Typen von TypeScript, weil es kein Standard ist.
 */
export interface InstallierenEreignis extends Event {
  prompt(): Promise<void>;
  readonly userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

/** Ob Gut gesagt gerade als App läuft (vom Home- oder Startbildschirm gestartet). */
export const ALS_APP_GESTARTET = new InjectionToken<() => boolean>('ALS_APP_GESTARTET', {
  providedIn: 'root',
  factory: () => () => {
    const g = geraetAusBrowser();
    return g.alsAppGestartet || g.standalone === true;
  },
});

/**
 * Hält das Angebot des Browsers, Gut gesagt als App zu installieren (18.11.2026), damit
 * Band und Hilfe denselben Stand zeigen. Chrome und Edge melden mit `beforeinstallprompt`,
 * dass sie installieren können; das Ereignis wird abgefangen (kein eigenes Banner des
 * Browsers) und gemerkt, bis jemand „Installieren“ drückt. Safari und Firefox melden
 * nichts: Dann gibt es keinen Knopf, nur die Anleitung in der Hilfe. Nichts davon landet
 * im Speicher des Browsers.
 */
@Injectable({ providedIn: 'root' })
export class AppInstallierenService {
  private ereignis: InstallierenEreignis | null = null;
  private readonly _installierbar = signal(false);
  private readonly _installiert = signal(inject(ALS_APP_GESTARTET)());

  /** Der Browser bietet das Installieren an: Ein Knopf „Installieren“ kann es auslösen. */
  readonly installierbar = this._installierbar.asReadonly();
  /** Gut gesagt läuft als App oder wurde in diesem Besuch installiert. */
  readonly installiert = this._installiert.asReadonly();
  /** Jede Änderung an `installierbar` oder `installiert`, für das Band. */
  readonly geaendert$ = new Subject<void>();

  constructor() {
    const fenster = inject(DOCUMENT).defaultView;
    if (!fenster) return;
    const angeboten = (e: Event): void => {
      e.preventDefault();
      this.ereignis = e as InstallierenEreignis;
      this.setzen(true, this._installiert());
    };
    const installiert = (): void => {
      this.ereignis = null;
      this.setzen(false, true);
    };
    fenster.addEventListener('beforeinstallprompt', angeboten);
    fenster.addEventListener('appinstalled', installiert);
    inject(DestroyRef).onDestroy(() => {
      fenster.removeEventListener('beforeinstallprompt', angeboten);
      fenster.removeEventListener('appinstalled', installiert);
    });
  }

  /**
   * Zeigt den Dialog des Browsers. Das Ereignis gilt nur einmal: Danach ist kein Knopf
   * mehr da, bis der Browser es neu meldet. Ohne Ereignis passiert nichts (null).
   */
  async installieren(): Promise<'accepted' | 'dismissed' | null> {
    const e = this.ereignis;
    if (!e) return null;
    this.ereignis = null;
    try {
      await e.prompt();
      const { outcome } = await e.userChoice;
      this.setzen(false, this._installiert() || outcome === 'accepted');
      return outcome;
    } catch {
      // Schon benutzt oder vom Browser verweigert: wie abgelehnt
      this.setzen(false, this._installiert());
      return 'dismissed';
    }
  }

  private setzen(installierbar: boolean, installiert: boolean): void {
    this._installierbar.set(installierbar && !installiert);
    this._installiert.set(installiert);
    this.geaendert$.next();
  }
}
