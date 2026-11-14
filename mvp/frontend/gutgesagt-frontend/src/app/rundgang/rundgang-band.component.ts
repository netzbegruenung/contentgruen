import { DOCUMENT } from '@angular/common';
import { Component, computed, inject, input } from '@angular/core';
import { RundgangService } from './rundgang.service';

/**
 * Bietet einen Rundgang an, ohne etwas zu verdecken (#587): ein
 * gelbes Band mit Daumen über dem Inhalt statt eines Fensters (Look nach #389,
 * Variante B). Kein Fokusfang, kein Schleier; wer weiterliest, liest weiter.
 * Ein Angebot ohne Rundgang (Hinweis „Gut gesagt als App“) hat nur „Ausblenden“.
 */
@Component({
  selector: 'app-rundgang-band',
  standalone: true,
  template: `
    @if (angebot(); as angebot) {
      <aside class="band" aria-labelledby="rundgang-band-titel">
        <img class="daumen" [class.symbol]="!!angebot.bild" [src]="angebot.bild ?? 'marke/daumen.svg'" alt="" width="48" height="48" />
        <div class="text">
          <h2 id="rundgang-band-titel">{{ angebot.titel }}</h2>
          <p>
            {{ angebot.satz }}
            @if (angebot.nachTeilenSymbol) {
              <!-- Das Teilen-Symbol von iOS: Quadrat mit Pfeil nach oben -->
              <svg class="teilen-symbol" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false">
                <path d="M8.5 9.5H6.5v11h11v-11h-2" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
                <path d="M12 3v11.5M8.5 6.5 12 3l3.5 3.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
              {{ angebot.nachTeilenSymbol }}
            }
          </p>
        </div>
        <div class="knoepfe">
          @if (angebot.ja) {
            <button type="button" class="rundgang-knopf voll" (click)="rundgang.bandBeantworten(true)">{{ angebot.ja }}</button>
          }
          <button type="button" class="rundgang-knopf text" [attr.aria-label]="angebot.neinLabel ?? null" (click)="ausblenden()">{{ angebot.nein }}</button>
        </div>
      </aside>
    }
  `,
  styleUrls: ['./rundgang-knoepfe.css', './rundgang-band.component.css'],
})
export class RundgangBandComponent {
  protected readonly rundgang = inject(RundgangService);
  private readonly dokument = inject(DOCUMENT);
  /**
   * Wo dieses Band steht: „kopf“ ueber jedem Seiteninhalt (app.component), „start“ auf
   * der Startseite unter dem Suchfeld. Ein Angebot mit `imInhalt` zeigt nur das Band
   * auf seiner Seite, alle anderen nur das im Kopf (Nutzerfuehrung 13.11.).
   */
  readonly ort = input<'kopf' | 'start'>('kopf');
  protected readonly angebot = computed(() => {
    const angebot = this.rundgang.band();
    return angebot && !!angebot.imInhalt === (this.ort() === 'start') ? angebot : null;
  });

  /**
   * Mit dem Band verschwindet der Knopf, der den Fokus hatte: Er geht an den Hauptinhalt
   * statt an den Seitenanfang. Nicht ins Suchfeld, sonst klappt am Handy die Tastatur auf.
   */
  protected ausblenden(): void {
    this.rundgang.bandBeantworten(false);
    const haupt = this.dokument.querySelector<HTMLElement>('main');
    if (!haupt) return;
    if (!haupt.hasAttribute('tabindex')) haupt.setAttribute('tabindex', '-1');
    haupt.focus({ preventScroll: true });
  }
}
