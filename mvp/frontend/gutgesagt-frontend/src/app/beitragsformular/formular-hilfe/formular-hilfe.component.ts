import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

import { FormularTyp } from '../../shared/formular-adresse';
import { HilfeUmschalterComponent } from '../../shared/components/hilfe-umschalter/hilfe-umschalter.component';
import { FORMULAR_HILFE, FormularHilfe } from './formular-hilfe-texte';
import { typEmoji } from '../../shared/content-type-registry';
import {
  ERFUNDENES_MELDEN,
  NICHT_JEDE_AUSSAGE,
  SCHREIBHILFEN,
  SCHREIBREGELN,
  TITEL_BEISPIELE,
  TYPEN_MIT_SCHREIBREGELN,
  TYPEN_MIT_TITELBEISPIELEN,
} from './schreibregeln';

/**
 * Kopf eines Beitragsformulars: eine Zeile, worauf es ankommt, und hinter dem ?
 * die Regeln (Ist / Ist nicht / Beispiel), bei Kommentar und Post dazu die
 * Schreibregeln und Schreibhilfen. Anfangs zu, ohne Merker. Sperrt nichts.
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

  readonly schreibregeln = SCHREIBREGELN;
  readonly schreibhilfen = SCHREIBHILFEN;
  readonly titelBeispiele = TITEL_BEISPIELE;
  readonly nichtJedeAussage = NICHT_JEDE_AUSSAGE;
  readonly erfundenesMelden = ERFUNDENES_MELDEN;

  get hilfe(): FormularHilfe | undefined {
    return FORMULAR_HILFE[this.typ];
  }

  /** Das Symbol des Typs wie im Kartenkopf - der Bezug zur Karte, die hier entsteht. */
  get emoji(): string {
    return typEmoji(this.typ);
  }

  get mitSchreibregeln(): boolean {
    return TYPEN_MIT_SCHREIBREGELN.includes(this.typ);
  }

  get mitTitelbeispielen(): boolean {
    return TYPEN_MIT_TITELBEISPIELEN.includes(this.typ);
  }

  get panelId(): string {
    return `formular-hilfe-${this.typ}`;
  }
}
