import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import {
  Art9EinwilligungService,
  Art9EinwilligungStand,
  EINWILLIGUNG_PFAD,
  wortlautDatum,
  wortlautErsterSatz,
} from '../services/art9-einwilligung.service';
import { ROUTES } from '../shared/constants/app.constants';
import { HILFE_PARAM } from '../help-dialog/help-dialog.component';
import {
  BestaetigungsDialogComponent,
  BestaetigungsDialogDaten,
} from '../shared/components/bestaetigungs-dialog/bestaetigungs-dialog.component';

/**
 * Rueckfrage vor dem Widerruf (UX-Review B3): Er loescht die Bewertungen sofort und
 * legt den Loeschauftrag an (#661), beides laesst sich nicht zuruecknehmen.
 */
export const WIDERRUF_FRAGE: BestaetigungsDialogDaten = {
  titel: 'Einwilligung widerrufen?',
  text:
    'Deine Bewertungen werden sofort gelöscht. Innerhalb von sieben Tagen werden deine Beiträge, ' +
    'Einwürfe und Sätze von dir gelöst. Danach kannst du nichts mehr beitragen und nichts bewerten, ' +
    'bis du neu einwilligst.',
  ja: 'Widerrufen',
  nein: 'Abbrechen',
};

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
  imports: [CommonModule, FormsModule, RouterModule, MatButtonModule, MatCardModule, MatCheckboxModule, MatDialogModule],
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
    private dialog: MatDialog,
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

  /** Beim Einwilligen kam 400: Der Wortlaut hat sich seit dem Laden geaendert. */
  wortlautGeaendert = false;

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
      error: (fehler) => {
        if (fehler?.status === 400) {
          // Der gezeigte Wortlaut gilt nicht mehr (etwa ein Tab von gestern): den aktuellen
          // selbst laden und darueber sagen, dass er neu zu lesen ist.
          this.wortlautGeaendert = true;
          this.laden();
          return;
        }
        this.zustand = 'fehler';
      },
    });
  }

  /**
   * Ohne Einwilligung weiter: lesen und suchen geht, beitragen und bewerten nicht. Kam
   * die Anmeldung aus der Hilfe (HILFE_PARAM), öffnet sie sich danach nicht wieder: Sie
   * böte nur Selbst beitragen an, und das geht ohne Einwilligung nicht. Die App merkt
   * sich die Entscheidung und fuehrt nicht bei jedem Start wieder her (B2).
   */
  ohneEinwilligung(): void {
    if (this.stand) {
      this.einwilligung.ohneMerken(this.stand.aktueller_wortlaut.kennung);
    }
    this.weiter(true);
  }

  widerrufenKlick(): void {
    const erlaubt = this.zustand === 'eingewilligt' || (this.zustand === 'frage' && this.fruehereEinwilligung);
    if (!erlaubt || this.rueckfrageOffen) {
      return;
    }
    // Ein Doppelklick oeffnete sonst zwei Rueckfragen.
    this.rueckfrageOffen = true;
    this.dialog
      .open(BestaetigungsDialogComponent, { data: WIDERRUF_FRAGE, autoFocus: 'dialog' })
      .afterClosed()
      .subscribe((ja) => {
        this.rueckfrageOffen = false;
        if (ja === true) this.widerrufen();
      });
  }

  /** Die Rueckfrage vor dem Widerruf ist offen. */
  private rueckfrageOffen = false;

  private widerrufen(): void {
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
  private weiter(ohneHilfe = false): void {
    const ziel = this.route.snapshot.queryParamMap.get('returnUrl');
    const sicher = ziel && ziel.startsWith('/') && !ziel.startsWith('//') && !ziel.startsWith(EINWILLIGUNG_PFAD);
    let url = sicher ? ziel : ROUTES.SEARCH;
    const baum = this.router.parseUrl(url);
    if (ohneHilfe && HILFE_PARAM in baum.queryParams) {
      const { [HILFE_PARAM]: _weg, ...rest } = baum.queryParams;
      baum.queryParams = rest;
      url = this.router.serializeUrl(baum);
    }
    this.router.navigateByUrl(url);
  }
}
