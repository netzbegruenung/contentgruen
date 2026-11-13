import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

import { BeitragskarteComponent } from './beitragskarte.component';
import { KartenDaten, KartenVariante } from './karten-daten';

/**
 * Beitragskarten auf hellgrauem Grund. Voll untereinander: mobil (bis 599 px)
 * zeigen Startseite und Suche diese Liste statt des Karussells. Mit raster stehen
 * volle Karten ab 600 px nebeneinander in Spalten zu 450 px, so viele die Breite
 * hergibt, mittig im Rahmen (Treffer der Suche am Desktop, #602). Kompakt als Album
 * (Meine Beitraege): Raster direkt auf dem Seitengrund, 2 Spalten, 3 ab 600 px,
 * 4 ab 960 px. Untereinander ist jede Karte so hoch, wie ihr Inhalt es verlangt;
 * in Spalten oder im Album sind die Karten einer Reihe gleich hoch.
 */
@Component({
  selector: 'app-kartenliste',
  standalone: true,
  imports: [CommonModule, BeitragskarteComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <ul
      class="kartenliste"
      [class.kartenliste--raster]="variante === 'kompakt'"
      [class.kartenliste--spalten]="raster && variante === 'voll'"
    >
      <li *ngFor="let karte of daten; trackBy: nachId">
        <app-beitragskarte [daten]="karte" [variante]="variante" (angetippt)="angetippt.emit($event)">
        </app-beitragskarte>
      </li>
    </ul>
  `,
  styles: [
    `
      .kartenliste {
        display: flex;
        flex-direction: column;
        gap: 16px;
        margin: 0;
        padding: 16px;
        list-style: none;
        background: var(--kartenliste-bg);
      }

      .kartenliste--raster {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 12px;
        padding: 0;
        background: none;
      }

      @media (min-width: 600px) {
        .kartenliste--raster {
          grid-template-columns: repeat(3, minmax(0, 1fr));
        }

        .kartenliste--spalten {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(0, 450px));
          /* Restbreite gleich auf beide Seiten statt rechts leer (Designrunde 12.11.) */
          justify-content: center;
          gap: 24px;
          padding: 24px;
          border-radius: var(--border-radius-medium);
        }
      }

      @media (min-width: 960px) {
        .kartenliste--raster {
          grid-template-columns: repeat(4, minmax(0, 1fr));
        }
      }
    `,
  ],
})
export class KartenlisteComponent {
  @Input() daten: KartenDaten[] = [];
  @Input() variante: KartenVariante = 'voll';
  /** Volle Karten ab 600 px in Spalten statt untereinander. */
  @Input() raster = false;

  /** Tipp auf eine antippbare Karte, unveraendert durchgereicht. */
  @Output() angetippt = new EventEmitter<KartenDaten>();

  nachId(_index: number, karte: KartenDaten): string {
    return karte.id;
  }
}
