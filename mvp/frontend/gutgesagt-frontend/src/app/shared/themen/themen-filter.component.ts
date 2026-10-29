import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Thema } from '../../services/dtos/themenDtos';

/**
 * Nach einem Thema filtern: "Alle" und je Thema ein Knopf, genau einer ist aktiv.
 * Welche Themen zur Wahl stehen, entscheidet die Seite.
 */
@Component({
  selector: 'app-themen-filter',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="themen-filter" role="group" aria-label="Nach Thema filtern">
      <button type="button" class="thema-chip" [class.gewaehlt]="aktiv === null"
              [attr.aria-pressed]="aktiv === null"
              (click)="waehlen(null)">Alle Themen</button>
      <button *ngFor="let thema of themen" type="button" class="thema-chip"
              [class.gewaehlt]="aktiv === thema.schluessel"
              [attr.aria-pressed]="aktiv === thema.schluessel"
              (click)="waehlen(thema.schluessel)">{{ thema.name }}</button>
    </div>
  `,
  styleUrls: ['./themen.css'],
})
export class ThemenFilterComponent {
  @Input() themen: Thema[] = [];
  /** Der Schluessel des aktiven Themas; null = alle. */
  @Input() aktiv: string | null = null;
  @Output() aktivChange = new EventEmitter<string | null>();

  waehlen(schluessel: string | null): void {
    if (schluessel !== this.aktiv) {
      this.aktivChange.emit(schluessel);
    }
  }
}
