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
      error: (e: HttpErrorResponse) => (this.stand = e.status === 410 ? 'ungueltig' : 'fehler'),
    });
  }
}
