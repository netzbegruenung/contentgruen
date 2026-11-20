import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

import { BeitragskarteComponent } from './beitragskarte.component';
import { KartenDaten, KartenKennzahlen, KartenVariante } from './karten-daten';

/**
 * Beitragskarten auf hellgrauem Grund. Voll untereinander: mobil (bis 599 px)
 * zeigen Startseite und Suche diese Liste statt des Karussells. Mit raster stehen
 * volle Karten ab 600 px nebeneinander in Spalten zu 450 px, so viele die Breite
 * hergibt, mittig im Rahmen (Treffer der Suche am Desktop, #602). Untereinander ist
 * jede Karte so hoch, wie ihr Inhalt es verlangt; in Spalten sind die Karten einer
 * Reihe gleich hoch.
 */
@Component({
  selector: 'app-kartenliste',
  standalone: true,
  imports: [CommonModule, BeitragskarteComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <ul
      class="kartenliste"
      [class.kartenliste--spalten]="raster && variante === 'voll' && !schlicht"
      [class.kartenliste--schlicht]="schlicht"
    >
      <li *ngFor="let karte of daten; trackBy: nachId">
        <app-beitragskarte [daten]="karte" [variante]="variante" [titelEbene]="titelEbene"
                           [antwortAufZeigen]="antwortAufZeigen" [schlank]="schlank"
                           [schlicht]="schlicht" [aufklappbar]="aufklappbar"
                           (kennzahlen)="kennzahlen.emit($event)">
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
        background: var(--kartenliste-grund);
        border: var(--kartenliste-rand);
      }

      /* Trefferseite (V3): ohne Grund, Rahmen und Innenabstand, eine Spalte */
      .kartenliste--schlicht {
        gap: 12px;
        padding: 0;
        background: none;
        border: none;
      }

      @media (min-width: 600px) {
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
    `,
  ],
})
export class KartenlisteComponent {
  @Input() daten: KartenDaten[] = [];
  @Input() variante: KartenVariante = 'voll';
  /** Volle Karten ab 600 px in Spalten statt untereinander. */
  @Input() raster = false;
  /** Durchgereicht an die Karten: Ebene der Titel-Ueberschrift (Standard h3). */
  @Input() titelEbene: 3 | 4 = 3;
  /** Durchgereicht an die Karten: Zeile "Antwort auf:" (aus, wo die Seite die Aussage nennt). */
  @Input() antwortAufZeigen = true;
  /** Durchgereicht an die Karten: ohne "passt auf Mastodon/Bluesky/X" und Alter (Startseite). */
  @Input() schlank = false;
  /** Durchgereicht an die Karten: schlichte Karte der Trefferseite; die Liste dann ohne Grund und Rahmen. */
  @Input() schlicht = false;
  /** Durchgereicht an die Karten: eingeklappt bis zum Antippen. */
  @Input() aufklappbar = false;

  /** Guete oder Nutzung einer Karte geaendert, unveraendert durchgereicht. */
  @Output() kennzahlen = new EventEmitter<KartenKennzahlen>();

  nachId(_index: number, karte: KartenDaten): string {
    return karte.id;
  }
}
