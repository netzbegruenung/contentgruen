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
  wortlautDatum,
  wortlautErsterSatz,
} from '../services/art9-einwilligung.service';
import { ROUTES } from '../shared/constants/app.constants';

type Zustand = 'laedt' | 'frage' | 'sendet' | 'eingewilligt' | 'widerruft' | 'fehler';

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

  constructor(
    private einwilligung: Art9EinwilligungService,
    private route: ActivatedRoute,
    private router: Router,
  ) {}

  /** Label am Haekchen: der erste Satz des aktuellen Wortlauts, unveraendert (#620). */
  get labelSatz(): string {
    return this.stand ? wortlautErsterSatz(this.stand.aktueller_wortlaut.text) : '';
  }

  /** Stand-Datum des Wortlauts, dem die Person zugestimmt hat (Kennung ggf. mit Suffix). */
  get wortlautVom(): string | null {
    return wortlautDatum(this.stand?.wortlaut);
  }

  /**
   * Eingewilligt zu einem frueheren Wortlaut und nicht widerrufen: Das Backend meldet
   * dann nicht eingewilligt (nur der aktuelle Wortlaut zaehlt, seit 2026-11-13), die
   * Einwilligung bleibt aber widerrufbar.
   */
  get fruehereEinwilligung(): boolean {
    const s = this.stand;
    return !!s && !s.eingewilligt && !!s.wortlaut && !s.widerrufen_am;
  }

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
    const erlaubt = this.zustand === 'eingewilligt' || (this.zustand === 'frage' && this.fruehereEinwilligung);
    if (!erlaubt) {
      return;
    }
    // Aus der Frage heraus bleibt die Frage stehen (gesperrt), statt kurz den Block fuer
    // Eingewilligte zu zeigen.
    this.zustand = this.zustand === 'frage' ? 'sendet' : 'widerruft';
    this.einwilligung.widerrufen().subscribe({
      next: () => this.laden(),
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
