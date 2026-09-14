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
        gap: var(--spacing-md);
        margin: 0;
        padding: var(--spacing-sm) var(--page-margin) var(--spacing-md);
        list-style: none;
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
