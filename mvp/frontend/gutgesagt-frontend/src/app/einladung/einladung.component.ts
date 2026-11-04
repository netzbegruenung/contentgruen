import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { EinladungService } from '../shared/einladung/einladung.service';

type Stand = 'pruefe' | 'ungueltig' | 'formular' | 'sendet' | 'gesendet' | 'fehler';
/** Warum Einloesen scheiterte, nach dem Status der Antwort (api/v1/einladungen.py). */
type Fehler = 'adresse' | 'zu_oft' | 'nicht_eingerichtet' | 'unbekannt';

const FEHLER_NACH_STATUS: Record<number, Fehler> = {
  422: 'adresse',
  429: 'zu_oft',
  503: 'nicht_eingerichtet',
};

/** Was der Screenreader beim Wechsel des Stands ansagt; die sichtbaren Texte stehen im Template. */
const ANSAGE: Record<Stand, string> = {
  pruefe: 'Einladung wird geprüft …',
  ungueltig: 'Diese Einladung gilt nicht (mehr).',
  formular: '',
  sendet: 'Konto wird angelegt …',
  gesendet: 'Schau in dein Postfach.',
  // Die Fehlertexte stehen mit role="alert" im Template.
  fehler: '',
};

/**
 * Eine Einladung einloesen (#429): Mail-Adresse eingeben, Gut gesagt legt das Konto
 * an, Keycloak schickt die Mail zum Festlegen des Passworts. Der Code steht hinter #
 * im Link (einladungslink), damit er in keinem Server-Log landet.
 */
@Component({
  selector: 'app-einladung',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, MatButtonModule, MatCardModule, MatFormFieldModule, MatInputModule],
  templateUrl: './einladung.component.html',
  styleUrls: ['./einladung.component.css'],
})
export class EinladungComponent implements OnInit {
  stand: Stand = 'pruefe';
  fehler: Fehler = 'unbekannt';
  email = '';
  private code = '';

  constructor(
    private route: ActivatedRoute,
    private einladungService: EinladungService,
  ) {}

  ngOnInit() {
    this.code = (this.route.snapshot.fragment ?? '').trim();
    if (!this.code) {
      this.stand = 'ungueltig';
      return;
    }
    this.einladungService.pruefen(this.code).subscribe({
      next: (einloesbar) => (this.stand = einloesbar ? 'formular' : 'ungueltig'),
      // Pruefen ist nur Komfort: Im Zweifel das Formular zeigen, Einloesen prueft erneut.
      error: () => (this.stand = 'formular'),
    });
  }

  einloesen() {
    const email = this.email.trim();
    if (!email || this.stand === 'sendet') {
      return;
    }
    this.stand = 'sendet';
    this.einladungService.einloesen(this.code, email).subscribe({
      next: () => (this.stand = 'gesendet'),
      error: (e: HttpErrorResponse) => {
        if (e.status === 410) {
          this.stand = 'ungueltig';
          return;
        }
        this.fehler = FEHLER_NACH_STATUS[e.status] ?? 'unbekannt';
        this.stand = 'fehler';
      },
    });
  }

  get ansage(): string {
    return ANSAGE[this.stand];
  }
}
