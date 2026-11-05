import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';
import {
  Art9EinwilligungService,
  Art9EinwilligungStand,
  EINWILLIGUNG_PFAD,
} from '../services/art9-einwilligung.service';
import { ROUTES } from '../shared/constants/app.constants';

type Zustand = 'laedt' | 'frage' | 'sendet' | 'eingewilligt' | 'fehler';

/**
 * Die Art.-9-Einwilligung (#489): ein eigenes Haekchen, getrennt von den
 * Nutzungsbedingungen und nichts vorbelegt. Nach dem ersten Anmelden fuehrt die App
 * hierher (Art9EinwilligungService.starten), spaeter das Profilmenue; wer
 * eingewilligt hat, sieht hier den Stand und kann widerrufen.
 *
 * Den Wortlaut liefert das Backend (domain/art9_einwilligung.py), damit er an einer
 * Stelle steht; mitgeschickt wird seine Kennung, gespeichert werden sie und der
 * Zeitpunkt.
 */
@Component({
  selector: 'app-einwilligung',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, MatButtonModule, MatCardModule, MatCheckboxModule],
  templateUrl: './einwilligung.component.html',
  styleUrls: ['./einwilligung.component.css'],
})
export class EinwilligungComponent implements OnInit {
  zustand: Zustand = 'laedt';
  stand?: Art9EinwilligungStand;
  angehakt = false;
  /** Nach einem Widerruf auf dieser Seite: Bestaetigung ueber der erneuten Frage. */
  widerrufen = false;

  constructor(
    private einwilligung: Art9EinwilligungService,
    private route: ActivatedRoute,
    private router: Router,
  ) {}

  ngOnInit(): void {
    this.laden();
  }

  private laden(): void {
    this.zustand = 'laedt';
    this.einwilligung.stand().subscribe({
      next: (stand) => {
        this.stand = stand;
        this.angehakt = false;
        this.zustand = stand.eingewilligt ? 'eingewilligt' : 'frage';
      },
      error: () => (this.zustand = 'fehler'),
    });
  }

  einwilligen(): void {
    if (!this.stand || !this.angehakt || this.zustand === 'sendet') {
      return;
    }
    this.zustand = 'sendet';
    this.einwilligung.einwilligen(this.stand.aktueller_wortlaut.kennung).subscribe({
      next: () => this.weiter(),
      error: () => (this.zustand = 'fehler'),
    });
  }

  /** Ohne Einwilligung weiter: lesen und suchen geht, beitragen und bewerten nicht. */
  ohneEinwilligung(): void {
    this.weiter();
  }

  widerrufenKlick(): void {
    this.einwilligung.widerrufen().subscribe({
      next: () => {
        this.widerrufen = true;
        this.laden();
      },
      error: () => (this.zustand = 'fehler'),
    });
  }

  nochmal(): void {
    this.laden();
  }

  /** Zurueck, woher die Person kam; nur Pfade innerhalb der App. */
  private weiter(): void {
    const ziel = this.route.snapshot.queryParamMap.get('returnUrl');
    const sicher = ziel && ziel.startsWith('/') && !ziel.startsWith('//') && !ziel.startsWith(EINWILLIGUNG_PFAD);
    this.router.navigateByUrl(sicher ? ziel : ROUTES.SEARCH);
  }
}
