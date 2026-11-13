import { DOCUMENT } from '@angular/common';
import { Injectable, inject, signal } from '@angular/core';

export type Farbschema = 'light' | 'dark';

/** Hier merkt sich die App die eigene Wahl; dasselbe liest das Skript in index.html. */
export const FARBSCHEMA_SCHLUESSEL = 'gutgesagt-farbschema';

const SYSTEM_DUNKEL = '(prefers-color-scheme: dark)';

/**
 * Hell oder dunkel. Ohne eigene Wahl gilt die Einstellung des Geräts, auch wenn sie sich
 * ändert; ein Klick auf den Umschalter merkt sich das Gegenteil im localStorage. Die Palette
 * hängt am Attribut data-theme des <html> (custom-theme.scss). Das Skript in index.html setzt
 * es schon vor dem ersten Bild, damit nichts aufblitzt; dieser Dienst setzt es beim Start
 * noch einmal (falls das Skript nicht lief) und bei jedem Wechsel.
 *
 * Ohne Speicher (privates Fenster, gesperrter Speicher) gilt die Wahl nur bis zum Neuladen.
 */
@Injectable({ providedIn: 'root' })
export class FarbschemaService {
  private readonly html = inject(DOCUMENT).documentElement;
  private readonly systemAbfrage: MediaQueryList | null =
    typeof window.matchMedia === 'function' ? window.matchMedia(SYSTEM_DUNKEL) : null;
  private readonly _schema = signal<Farbschema>(this.anfangsSchema());

  /** Das gerade gültige Schema. */
  readonly schema = this._schema.asReadonly();

  constructor() {
    this.anwenden(this._schema());
    this.systemAbfrage?.addEventListener?.('change', (ereignis) => {
      if (!gespeichert()) this.anwenden(ereignis.matches ? 'dark' : 'light');
    });
  }

  dunkel(): boolean {
    return this._schema() === 'dark';
  }

  /** Wechselt zum anderen Schema und merkt es sich. */
  umschalten(): void {
    const neu: Farbschema = this.dunkel() ? 'light' : 'dark';
    try {
      localStorage.setItem(FARBSCHEMA_SCHLUESSEL, neu);
    } catch {
      // Ohne Speicher gilt die Wahl bis zum Neuladen.
    }
    this.anwenden(neu);
  }

  private anfangsSchema(): Farbschema {
    return gespeichert() ?? (this.systemAbfrage?.matches ? 'dark' : 'light');
  }

  private anwenden(schema: Farbschema): void {
    this._schema.set(schema);
    this.html.setAttribute('data-theme', schema);
  }
}

function gespeichert(): Farbschema | null {
  try {
    const wert = localStorage.getItem(FARBSCHEMA_SCHLUESSEL);
    return wert === 'light' || wert === 'dark' ? wert : null;
  } catch {
    return null;
  }
}
