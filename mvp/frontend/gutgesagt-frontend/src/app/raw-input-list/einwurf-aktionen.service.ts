import { Injectable } from '@angular/core';
import { Router } from '@angular/router';
import { Clipboard } from '@angular/cdk/clipboard';
import { MatBottomSheet } from '@angular/material/bottom-sheet';
import { MatSnackBar } from '@angular/material/snack-bar';

import { EinwurfBeitragSheetComponent } from './einwurf-beitrag-sheet.component';
import { SCHRITT_PARAM } from '../destillieren/destillier-uebergabe.service';
import { EinwurfService } from '../services/einwurf.service';
import { LoggingService } from '../services/logging.service';
import { verwerfenFehlertext } from '../shared/fangkorb-texte';
import { EinwurfAktion, KartenDaten } from '../beitragskarte/karten-daten';

/**
 * Was der Griff auf einer Einwurf-Karte ausloest, gleich ob sie im Fangkorb oder
 * unter "Meine Einwuerfe" steht.
 *
 * Destillieren und Ausformulieren fuehren beide in die Destillier-Ansicht: Dort
 * steht der eigene Satz schon im Feld, und "Weiter" fuehrt zur Typwahl. Ein
 * eigenes Formular mit fremdem Satz gibt es nicht.
 */
@Injectable({ providedIn: 'root' })
export class EinwurfAktionenService {
  constructor(
    private einwurfService: EinwurfService,
    private router: Router,
    private logger: LoggingService,
    private bottomSheet: MatBottomSheet,
    private clipboard: Clipboard,
    private snackBar: MatSnackBar,
  ) {}

  /** ``nachVerwerfen``: Die Liste laedt neu, weil der Einwurf seine Stufe gewechselt hat. */
  ausfuehren(karte: KartenDaten, aktion: EinwurfAktion, nachVerwerfen: () => void): void {
    const angaben = karte.einwurfAngaben;
    if (!angaben) {
      return;
    }
    switch (aktion) {
      case 'ausformulieren':
        // Der Satz steht schon - dann beginnt das Ausformulieren bei der Typwahl,
        // nicht wieder im Satzfeld. Ohne eigenen Satz faellt die Ansicht selbst
        // auf das Satzfeld zurueck.
        this.router.navigate(['/destillieren', angaben.einwurfId], {
          queryParams: { [SCHRITT_PARAM]: 'typwahl' },
        });
        break;
      case 'destillieren':
      case 'weiterDestillieren':
        this.router.navigate(['/destillieren', angaben.einwurfId]);
        break;
      case 'ansehen':
        this.bottomSheet.open(EinwurfBeitragSheetComponent, {
          data: { beitraege: angaben.beitraege },
          ariaLabel: karte.titel || 'Beitrag zu diesem Einwurf',
        });
        break;
      case 'linkKopieren':
        this.linkKopieren(angaben.link);
        break;
      case 'verwerfen':
        this.verwerfen(angaben.einwurfId, nachVerwerfen);
        break;
    }
  }

  private linkKopieren(link: string | null): void {
    if (!link) {
      return;
    }
    const kopiert = this.clipboard.copy(link);
    this.snackBar.open(kopiert ? 'Link kopiert.' : 'Kopieren hat nicht geklappt.', undefined, {
      duration: 3000,
    });
  }

  private verwerfen(einwurfId: string, nachVerwerfen: () => void): void {
    this.einwurfService.updateStatus(einwurfId, 'discarded').subscribe({
      next: () => {
        this.snackBar.open('Verworfen.', undefined, { duration: 3000 });
        nachVerwerfen();
      },
      error: (error) => {
        this.logger.error('Einwurf konnte nicht verworfen werden', error);
        this.snackBar.open(verwerfenFehlertext(error?.status), 'OK', { duration: 6000 });
      },
    });
  }
}
