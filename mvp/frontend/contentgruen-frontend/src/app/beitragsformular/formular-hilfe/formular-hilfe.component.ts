import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

import { FormularTyp } from '../../shared/formular-adresse';
import { HilfeUmschalterComponent } from '../../shared/components/hilfe-umschalter/hilfe-umschalter.component';
import { FORMULAR_HILFE, FormularHilfe } from './formular-hilfe-texte';

/**
 * Kopf eines Beitragsformulars: eine Zeile, worauf es ankommt, und hinter dem ?
 * die Regeln (Ist / Ist nicht / Beispiel). Anfangs zu, ohne Merker.
 */
@Component({
  standalone: true,
  selector: 'app-formular-hilfe',
  imports: [CommonModule, HilfeUmschalterComponent],
  templateUrl: './formular-hilfe.component.html',
  styleUrls: ['./formular-hilfe.component.css'],
})
export class FormularHilfeComponent {
  @Input({ required: true }) typ!: FormularTyp;

  offen = false;

  get hilfe(): FormularHilfe | undefined {
    return FORMULAR_HILFE[this.typ];
  }

  get panelId(): string {
    return `formular-hilfe-${this.typ}`;
  }
}
