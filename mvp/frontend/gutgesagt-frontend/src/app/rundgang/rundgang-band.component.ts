import { Component, computed, inject, input } from '@angular/core';
import { RundgangService } from './rundgang.service';

/**
 * Bietet einen Rundgang an, ohne etwas zu verdecken (#587): ein
 * gelbes Band mit Daumen über dem Inhalt statt eines Fensters (Look nach #389,
 * Variante B). Kein Fokusfang, kein Schleier; wer weiterliest, liest weiter.
 */
@Component({
  selector: 'app-rundgang-band',
  standalone: true,
  template: `
    @if (angebot(); as angebot) {
      <aside class="band" aria-labelledby="rundgang-band-titel">
        <img class="daumen" src="marke/daumen.svg" alt="" width="48" height="48" />
        <div class="text">
          <h2 id="rundgang-band-titel">{{ angebot.titel }}</h2>
          <p>{{ angebot.satz }}</p>
        </div>
        <div class="knoepfe">
          <button type="button" class="rundgang-knopf voll" (click)="rundgang.bandBeantworten(true)">{{ angebot.ja }}</button>
          <button type="button" class="rundgang-knopf text" (click)="rundgang.bandBeantworten(false)">{{ angebot.nein }}</button>
        </div>
      </aside>
    }
  `,
  styleUrls: ['./rundgang-knoepfe.css', './rundgang-band.component.css'],
})
export class RundgangBandComponent {
  protected readonly rundgang = inject(RundgangService);
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
}
