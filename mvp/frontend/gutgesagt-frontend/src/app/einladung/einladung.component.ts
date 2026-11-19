import { Component, ElementRef, Injector, OnInit, ViewChild, afterNextRender, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { EinladungService } from '../shared/einladung/einladung.service';

type Stand = 'eingeben' | 'pruefe' | 'ungueltig' | 'formular' | 'sendet' | 'gesendet' | 'fehler';
/** Warum Einloesen scheiterte, nach dem Status der Antwort (api/v1/einladungen.py). */
type Fehler = 'adresse' | 'zu_oft' | 'nicht_eingerichtet' | 'unbekannt';

const FEHLER_NACH_STATUS: Record<number, Fehler> = {
  422: 'adresse',
  429: 'zu_oft',
  503: 'nicht_eingerichtet',
};

/** Was der Screenreader beim Wechsel des Stands ansagt; die sichtbaren Texte stehen im Template. */
const ANSAGE: Record<Stand, string> = {
  eingeben: '',
  pruefe: 'Einladung wird geprüft …',
  ungueltig: 'Diese Einladung gilt nicht (mehr).',
  formular: '',
  sendet: 'Konto wird angelegt …',
  gesendet: 'Schau in dein Postfach.',
  // Die Fehlertexte stehen mit role="alert" im Template.
  fehler: '',
};

/** Zeichen eines Codes: secrets.token_urlsafe im Backend, hoechstens CODE_MAX (api/v1/einladungen.py). */
const CODE_MUSTER = /^[A-Za-z0-9_-]{1,64}$/;

/**
 * Der Code aus dem, was jemand ins Feld einfuegt: der ganze Link (einladungslink) oder nur
 * das Stueck hinter #. Leerraum faellt weg, etwa ein Umbruch beim Kopieren aus einer Mail.
 * Was kein Code sein kann, gibt null; das Backend lehnte es sonst mit 422 ab, und das
 * Formular meldete eine falsche Mail-Adresse.
 */
export function codeAusEingabe(eingabe: string): string | null {
  const ohneLeerraum = eingabe.replace(/\s+/g, '');
  const raute = ohneLeerraum.lastIndexOf('#');
  const code = raute >= 0 ? ohneLeerraum.slice(raute + 1) : ohneLeerraum;
  return CODE_MUSTER.test(code) ? code : null;
}

/**
 * Eine Einladung einloesen (#429): Mail-Adresse eingeben, Gut gesagt legt das Konto
 * an, Keycloak schickt die Mail zum Festlegen des Passworts. Der Code steht hinter #
 * im Link (einladungslink), damit er in keinem Server-Log landet. Ohne Code, etwa ueber
 * „Einladung einlösen“ auf der Login-Seite, fragt die Seite nach dem Link.
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
  /** Der eingefuegte Link, solange die Seite ohne Code aufgerufen wurde. */
  link = '';
  linkFalsch = false;
  private code = '';
  /** Nach „Anderen Link einfügen“: Fokus ins Feld, sobald es wieder da ist; beim ersten Aufruf nicht. */
  private feldFokussieren = false;
  private readonly injector = inject(Injector);

  @ViewChild('linkFeld')
  set linkFeld(feld: ElementRef<HTMLInputElement> | undefined) {
    if (feld && this.feldFokussieren) {
      this.feldFokussieren = false;
      // Erst nach dem Rendern: Fokus mitten in der Change Detection aendert das Formularfeld
      afterNextRender(() => feld.nativeElement.focus(), { injector: this.injector });
    }
  }

  constructor(
    private route: ActivatedRoute,
    private einladungService: EinladungService,
  ) {}

  ngOnInit() {
    const code = (this.route.snapshot.fragment ?? '').trim();
    if (!code) {
      this.stand = 'eingeben';
      return;
    }
    this.pruefen(code);
  }

  /** Den eingefuegten Link uebernehmen und weiter wie beim Aufruf ueber den Link. */
  linkUebernehmen() {
    const code = codeAusEingabe(this.link);
    this.linkFalsch = !code;
    if (code) {
      this.pruefen(code);
    }
  }

  /** Nach einer Einladung, die nicht gilt: einen anderen Link einfuegen. */
  andererLink() {
    this.link = '';
    this.linkFalsch = false;
    this.feldFokussieren = true;
    this.stand = 'eingeben';
  }

  private pruefen(code: string) {
    this.code = code;
    this.stand = 'pruefe';
    this.einladungService.pruefen(code).subscribe({
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
