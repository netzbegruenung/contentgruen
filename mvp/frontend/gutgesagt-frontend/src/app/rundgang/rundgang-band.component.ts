import { Component, inject } from '@angular/core';
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
    @if (rundgang.band(); as angebot) {
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
}
