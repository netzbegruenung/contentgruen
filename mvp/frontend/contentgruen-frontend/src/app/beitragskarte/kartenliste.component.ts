import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

import { BeitragskarteComponent } from './beitragskarte.component';
import { KartenDaten, KartenVariante } from './karten-daten';

/**
 * Beitragskarten untereinander. Mobil (bis 599 px) zeigen Startseite und Suche diese
 * Liste statt des Karussells; jede Karte ist so hoch, wie ihr Inhalt es verlangt.
 */
@Component({
  selector: 'app-kartenliste',
  standalone: true,
  imports: [CommonModule, BeitragskarteComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <ul class="kartenliste">
      <li *ngFor="let karte of daten; trackBy: nachId">
        <app-beitragskarte [daten]="karte" [variante]="variante"></app-beitragskarte>
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
    `,
  ],
})
export class KartenlisteComponent {
  @Input() daten: KartenDaten[] = [];
  @Input() variante: KartenVariante = 'voll';

  nachId(_index: number, karte: KartenDaten): string {
    return karte.id;
  }
}
