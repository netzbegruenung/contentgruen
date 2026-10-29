import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Thema } from '../../services/dtos/themenDtos';
import { HOECHSTENS_THEMEN_JE_AUSSAGE } from '../../services/themen.service';

/**
 * Ein bis zwei Themen fuer eine Aussage waehlen, optional. Jedes Thema ist ein
 * Umschalter; sind zwei gewaehlt, lassen sich weitere erst nach dem Abwaehlen
 * eines der beiden waehlen.
 */
@Component({
  selector: 'app-themen-auswahl',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="themen-auswahl" role="group" [attr.aria-label]="beschriftung">
      <button *ngFor="let thema of themen" type="button" class="thema-chip"
              [class.gewaehlt]="istGewaehlt(thema)"
              [attr.aria-pressed]="istGewaehlt(thema)"
              [disabled]="!istGewaehlt(thema) && voll"
              (click)="umschalten(thema)">{{ thema.name }}</button>
    </div>
    <p class="themen-hinweis">Bis zu zwei Themen, optional.</p>
  `,
  styleUrls: ['./themen.css'],
})
export class ThemenAuswahlComponent {
  @Input() themen: Thema[] = [];
  /** Die gewaehlten Schluessel. */
  @Input() gewaehlt: string[] = [];
  @Input() beschriftung = 'Themen';
  @Output() gewaehltChange = new EventEmitter<string[]>();

  get voll(): boolean {
    return this.gewaehlt.length >= HOECHSTENS_THEMEN_JE_AUSSAGE;
  }

  istGewaehlt(thema: Thema): boolean {
    return this.gewaehlt.includes(thema.schluessel);
  }

  umschalten(thema: Thema): void {
    if (this.istGewaehlt(thema)) {
      this.gewaehltChange.emit(this.gewaehlt.filter((s) => s !== thema.schluessel));
    } else if (!this.voll) {
      this.gewaehltChange.emit([...this.gewaehlt, thema.schluessel]);
    }
  }
}
