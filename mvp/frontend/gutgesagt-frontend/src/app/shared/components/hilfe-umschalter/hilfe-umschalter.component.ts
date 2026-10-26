import { Component, EventEmitter, Input, Output } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';

/**
 * Das ?-Icon, das eine Erklaerung auf- und zuklappt. Nur der Knopf: Wo die
 * Erklaerung steht, bestimmt die Seite (`steuert` ist ihre Element-ID).
 *
 * Merkt sich nichts - die Erklaerung ist anfangs zu, bis jemand danach fragt.
 */
@Component({
  standalone: true,
  selector: 'app-hilfe-umschalter',
  imports: [MatIconModule],
  template: `
    <button type="button" class="erklaerung-umschalter"
            [attr.aria-controls]="steuert"
            [attr.aria-expanded]="offen"
            [attr.aria-label]="offen ? beschriftungOffen : beschriftungZu"
            (click)="umschalten()">
      <mat-icon aria-hidden="true">help_outline</mat-icon>
    </button>
  `,
  styles: [`
    :host {
      display: contents;
    }

    /* Nur das Icon: kein Knopfrahmen, kein Schatten, trotzdem 40 px Tippflaeche */
    .erklaerung-umschalter {
      flex-shrink: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 40px;
      height: 40px;
      padding: 0;
      border: 0;
      border-radius: 50%;
      background: none;
      box-shadow: none;
      color: var(--primary-dark, #005437);
      cursor: pointer;
    }

    .erklaerung-umschalter mat-icon {
      width: 20px;
      height: 20px;
      font-size: 20px;
    }

    .erklaerung-umschalter:focus-visible {
      outline: 2px solid var(--primary-dark, #005437);
      outline-offset: 2px;
    }
  `],
})
export class HilfeUmschalterComponent {
  @Input() offen = false;
  @Output() offenChange = new EventEmitter<boolean>();
  /** ID des Elements mit der Erklaerung. */
  @Input({ required: true }) steuert!: string;
  @Input() beschriftungZu = 'Erklärung öffnen';
  @Input() beschriftungOffen = 'Erklärung schließen';

  umschalten(): void {
    this.offen = !this.offen;
    this.offenChange.emit(this.offen);
  }
}
