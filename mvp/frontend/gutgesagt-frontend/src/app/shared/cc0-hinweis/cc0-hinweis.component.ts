import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { CC0_ERKLAERUNG_URL, CONSENT_HINWEIS, ConsentHinweis } from '../consent-hinweis';

/**
 * Der CC0-Hinweis ueber dem Absende-Knopf (GLOSSARY.md, "CC0-Hinweis"): Mit dem Absenden
 * stellt die Person ihre Formulierung unter CC0 und stimmt den Nutzungsbedingungen zu (#415).
 * Beide verlinkt, jeweils im neuen Tab, damit das Formular offen bleibt.
 *
 * Als Attribut an einem `<p>`, damit der Absatz im Formular an seiner Stelle steht:
 * `<p appCc0Hinweis></p>`, beim Satz `<p appCc0Hinweis [hinweis]="CONSENT_HINWEIS_SATZ"></p>`.
 */
@Component({
  selector: 'p[appCc0Hinweis]',
  standalone: true,
  imports: [RouterLink],
  host: { class: 'submit-hint' },
  changeDetection: ChangeDetectionStrategy.OnPush,
  template:
    `{{ hinweis.vorCc0 }}<a [href]="cc0Url" target="_blank" rel="noopener">CC0</a>` +
    `{{ hinweis.nachCc0 }}<a routerLink="/nutzungsbedingungen" target="_blank" rel="noopener">Nutzungsbedingungen</a>` +
    `{{ hinweis.nachNutzungsbedingungen }}`,
})
export class Cc0HinweisComponent {
  @Input() hinweis: ConsentHinweis = CONSENT_HINWEIS;

  readonly cc0Url = CC0_ERKLAERUNG_URL;
}
