import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

import { BeitragskarteComponent } from './beitragskarte.component';
import { KartenDaten, KartenVariante } from './karten-daten';

/**
 * Beitragskarten auf hellgrauem Grund. Voll untereinander: mobil (bis 599 px)
 * zeigen Startseite und Suche diese Liste statt des Karussells. Kompakt als Album
 * (Meine Beitraege): Raster direkt auf dem Seitengrund, 2 Spalten, 3 ab 600 px,
 * 4 ab 960 px. Jede Karte ist so hoch, wie ihr Inhalt es verlangt.
 */
@Component({
  selector: 'app-kartenliste',
  standalone: true,
  imports: [CommonModule, BeitragskarteComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <ul class="kartenliste" [class.kartenliste--raster]="variante === 'kompakt'">
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

  /** Tipp auf eine antippbare Karte, unveraendert durchgereicht. */
  @Output() angetippt = new EventEmitter<KartenDaten>();

  nachId(_index: number, karte: KartenDaten): string {
    return karte.id;
  }
}
