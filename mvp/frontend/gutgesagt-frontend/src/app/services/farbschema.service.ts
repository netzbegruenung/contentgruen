import { DOCUMENT } from '@angular/common';
import { DestroyRef, Injectable, inject, signal } from '@angular/core';

export type Farbschema = 'light' | 'dark';

/** Hier merkt sich die App die eigene Wahl; dasselbe liest das Skript in index.html. */
export const FARBSCHEMA_SCHLUESSEL = 'gutgesagt-farbschema';

/**
 * Farbe der Browserleiste je Schema (meta theme-color): hell Klee, dunkel --bg-main der
 * Dunkel-Palette. Dieselben Werte stehen im Skript in index.html.
 */
export const LEISTENFARBE: Record<Farbschema, string> = { light: '#008939', dark: '#1e1f1e' };

const SYSTEM_DUNKEL = '(prefers-color-scheme: dark)';

/**
 * Hell oder dunkel. Ohne eigene Wahl gilt die Einstellung des Geräts, auch wenn sie sich
 * ändert. Ein Klick auf den Umschalter merkt sich die Wahl im localStorage; entspricht sie
 * der Geräteeinstellung, wird nichts gemerkt, die App folgt dann wieder dem Gerät. Die Palette
 * hängt am Attribut data-theme des <html> (custom-theme.scss). Das Skript in index.html setzt
 * es schon vor dem ersten Bild, damit nichts aufblitzt; dieser Dienst setzt es beim Start
 * noch einmal (falls das Skript nicht lief), bei jedem Wechsel und wenn ein anderer Tab
 * umschaltet (storage-Ereignis).
 *
 * Ohne Speicher (privates Fenster, gesperrter Speicher) gilt die Wahl nur bis zum Neuladen.
 */
@Injectable({ providedIn: 'root' })
export class FarbschemaService {
  private readonly dokument = inject(DOCUMENT);
  private readonly html = this.dokument.documentElement;
  private readonly systemAbfrage: MediaQueryList | null =
    typeof window.matchMedia === 'function' ? window.matchMedia(SYSTEM_DUNKEL) : null;
  private readonly _schema = signal<Farbschema>(this.anfangsSchema());

  /** Das gerade gültige Schema. */
  readonly schema = this._schema.asReadonly();

  private readonly geraetGewechselt = (): void => {
    if (!gespeichert()) this.anwenden(this.system());
  };

  /** Anderer Tab hat umgeschaltet oder die Wahl geloescht: ohne Neuladen nachziehen. */
  private readonly speicherGewechselt = (ereignis: StorageEvent): void => {
    if (ereignis.key !== FARBSCHEMA_SCHLUESSEL && ereignis.key !== null) return;
    this.anwenden(gespeichert() ?? this.system());
  };

  constructor() {
    this.anwenden(this._schema());
    this.systemAbfrage?.addEventListener?.('change', this.geraetGewechselt);
    window.addEventListener('storage', this.speicherGewechselt);
    inject(DestroyRef).onDestroy(() => {
      this.systemAbfrage?.removeEventListener?.('change', this.geraetGewechselt);
      window.removeEventListener('storage', this.speicherGewechselt);
    });
  }

  dunkel(): boolean {
    return this._schema() === 'dark';
  }

  /** Wechselt zum anderen Schema; merkt es sich nur, wenn es vom Gerät abweicht. */
  umschalten(): void {
    const neu: Farbschema = this.dunkel() ? 'light' : 'dark';
    try {
      if (neu === this.system()) localStorage.removeItem(FARBSCHEMA_SCHLUESSEL);
      else localStorage.setItem(FARBSCHEMA_SCHLUESSEL, neu);
    } catch {
      // Ohne Speicher gilt die Wahl bis zum Neuladen.
    }
    this.anwenden(neu);
  }

  private system(): Farbschema {
    return this.systemAbfrage?.matches ? 'dark' : 'light';
  }

  private anfangsSchema(): Farbschema {
    return gespeichert() ?? this.system();
  }

  private anwenden(schema: Farbschema): void {
    this._schema.set(schema);
    this.html.setAttribute('data-theme', schema);
    this.dokument.querySelector('meta[name="theme-color"]')?.setAttribute('content', LEISTENFARBE[schema]);
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
