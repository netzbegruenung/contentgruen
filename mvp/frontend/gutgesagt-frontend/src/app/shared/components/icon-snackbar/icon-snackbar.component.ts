import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import {
  MAT_SNACK_BAR_DATA,
  MatSnackBarAction,
  MatSnackBarActions,
  MatSnackBarLabel,
  MatSnackBarRef,
} from '@angular/material/snack-bar';

/** Was die Snackbar mit Symbol zeigt. */
export interface IconSnackbarDaten {
  /** Ein dekoratives Symbol, etwa ein Emoji; Screenreader lesen es nicht vor. */
  icon: string;
  text: string;
  aktion: string;
}

/**
 * Wie die einfache Snackbar von Material (Text und ein Knopf), mit einem Symbol vorn
 * (Sofort-Dank nach einer Stimme, Entscheidung 20.11.2026). Das Symbol ist dekorativ und
 * steht in einem eigenen Element mit aria-hidden: Material sagt den Inhalt der Snackbar
 * über seinen Live-Bereich an, und so hört man nur den Text, nicht „Sämling“ oder
 * „Daumen hoch“. In einem einfachen Snackbar-Text ließe sich das Emoji nicht verstecken.
 */
@Component({
  selector: 'app-icon-snackbar',
  standalone: true,
  imports: [MatButtonModule, MatSnackBarLabel, MatSnackBarActions, MatSnackBarAction],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div matSnackBarLabel class="icon-snackbar-text">
      <span class="icon-snackbar-icon" aria-hidden="true">{{ daten.icon }}</span>
      <span>{{ daten.text }}</span>
    </div>
    <div matSnackBarActions>
      <button mat-button matSnackBarAction type="button" (click)="ref.dismissWithAction()">{{ daten.aktion }}</button>
    </div>
  `,
  styles: [
    `
      :host {
        display: flex;
        align-items: center;
      }
      .icon-snackbar-text {
        display: flex;
        align-items: baseline;
        gap: 0.5em;
      }
      .icon-snackbar-icon {
        flex: none;
      }
    `,
  ],
})
export class IconSnackbarComponent {
  readonly daten = inject<IconSnackbarDaten>(MAT_SNACK_BAR_DATA);
  readonly ref = inject<MatSnackBarRef<IconSnackbarComponent>>(MatSnackBarRef);
}
