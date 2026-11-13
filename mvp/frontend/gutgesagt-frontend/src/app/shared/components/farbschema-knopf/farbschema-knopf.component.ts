import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';

import { FarbschemaService } from '../../../services/farbschema.service';

/**
 * Kleiner Umschalter hell/dunkel im Desktop-Kopf. Ein Knopf, zwei Zustände: Er zeigt, wohin
 * er schaltet (Mond im Hellen, Sonne im Dunkeln). Für Screenreader ein Schalter mit festem
 * Namen und aria-pressed. Mobil steht derselbe Wechsel im Menü (mobile-menu).
 */
@Component({
  selector: 'app-farbschema-knopf',
  standalone: true,
  imports: [MatIconModule, MatTooltipModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <button
      type="button"
      class="farbschema-knopf"
      aria-label="Dunkles Farbschema"
      [attr.aria-pressed]="farbschema.dunkel()"
      [matTooltip]="farbschema.dunkel() ? 'Hell anzeigen' : 'Dunkel anzeigen'"
      (click)="farbschema.umschalten()"
    >
      <mat-icon aria-hidden="true">{{ farbschema.dunkel() ? 'light_mode' : 'dark_mode' }}</mat-icon>
    </button>
  `,
  styles: [
    `
      :host {
        display: inline-flex;
      }

      .farbschema-knopf {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 40px;
        height: 40px;
        padding: 0;
        border: 0;
        border-radius: 50%;
        background: none;
        color: var(--primary-dark);
        cursor: pointer;
      }

      .farbschema-knopf:hover {
        background: var(--overlay-faint);
      }

      .farbschema-knopf:focus-visible {
        outline: 2px solid var(--akzent-tanne);
        outline-offset: 2px;
      }
    `,
  ],
})
export class FarbschemaKnopfComponent {
  protected readonly farbschema = inject(FarbschemaService);
}
