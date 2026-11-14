import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

/**
 * Was eine Liste sagt, deren Laden gescheitert ist: Spinner und Text, kein „bitte neu
 * laden“, denn sie laedt selbst nach (``selbstNachladen``). Ohne Fehler steht nichts da.
 *
 * ``geladen``: Es steht schon ein Stand da, der stehen bleibt. ``was``: der Name der
 * Liste am Satzanfang, etwa „Suchen ohne Treffer“.
 */
@Component({
  selector: 'app-nachlade-hinweis',
  standalone: true,
  imports: [MatProgressSpinnerModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (fehler) {
      <p class="nachlade-hinweis" role="status">
        <mat-spinner diameter="16" aria-hidden="true"></mat-spinner>
        <span>{{ geladen ? 'Aktualisieren gerade nicht möglich' : was + ' gerade nicht erreichbar' }}, neuer Versuch in Kürze …</span>
      </p>
    }
  `,
  styles: [`
    .nachlade-hinweis {
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 0 0 8px;
      font-size: 0.875rem;
      color: var(--text-secondary);
    }
  `],
})
export class NachladeHinweisComponent {
  @Input() fehler = false;
  @Input() geladen = false;
  @Input() was = 'Die Liste';
}
