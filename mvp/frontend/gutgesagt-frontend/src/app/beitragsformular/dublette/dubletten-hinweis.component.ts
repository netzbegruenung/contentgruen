import { Component, EventEmitter, Input, Output } from '@angular/core';
import { NgIf } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { Vorhanden, offeneEntscheidung } from './dublette';

/**
 * Der Hinweis auf eine Dublette im Kommentar- und im Hintergrundinfo-Formular: der
 * vorhandene Beitrag mit Titel und "Ansehen", darunter, solange die Person nicht
 * entschieden hat, ihre Wahl - einem fremden zustimmen, den eigenen nehmen oder
 * trotzdem speichern. Was die Knoepfe tun, entscheidet das Formular.
 */
@Component({
  standalone: true,
  selector: 'app-dubletten-hinweis',
  templateUrl: './dubletten-hinweis.component.html',
  styleUrls: ['./dubletten-hinweis.component.scss'],
  imports: [NgIf, MatButtonModule, MatProgressSpinnerModule],
})
export class DublettenHinweisComponent {
  @Input({ required: true }) vorhanden!: Vorhanden<unknown>;
  /** Der Hinweis, je nach Stand (dublettenHinweis). */
  @Input({ required: true }) hinweis!: string;
  @Input() kannZustimmen = false;
  @Input() kannNehmen = false;
  /** Beschriftung des Nehmen-Knopfs, im Genus des Beitragstyps. */
  @Input({ required: true }) nehmenText!: string;
  /** Ein Aufruf laeuft: alle Knoepfe gesperrt. */
  @Input() beschaeftigt = false;
  /** Nehmen geht gerade nicht (etwa: Aussage zu kurz). */
  @Input() nehmenGesperrt = false;
  /** Nehmen laeuft: Spinner im Knopf. */
  @Input() nimmt = false;
  /** Fehler beim Zustimmen oder Nehmen; die Entscheidung bleibt offen. */
  @Input() fehler: string | null = null;

  @Output() ansehen = new EventEmitter<void>();
  @Output() zustimmen = new EventEmitter<void>();
  @Output() nehmen = new EventEmitter<void>();
  @Output() trotzdem = new EventEmitter<void>();

  get offeneEntscheidung(): boolean {
    return offeneEntscheidung(this.vorhanden);
  }
}
