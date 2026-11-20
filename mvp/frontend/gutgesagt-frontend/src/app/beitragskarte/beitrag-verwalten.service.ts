import { Injectable } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { EMPTY, Observable, of } from 'rxjs';
import { catchError, map, switchMap, tap } from 'rxjs/operators';

import { KartenDaten } from './karten-daten';
import { MeineBeitraegeService } from '../services/meine-beitraege.service';
import { BeitragAendernDialogComponent } from './beitrag-aendern-dialog.component';
import {
  BestaetigungsDialogComponent,
  BestaetigungsDialogDaten,
} from '../shared/components/bestaetigungs-dialog/bestaetigungs-dialog.component';

export const LOESCHEN_FRAGE: BestaetigungsDialogDaten = {
  titel: 'Beitrag löschen?',
  text:
    'Niemand findet ihn danach mehr, auch nicht in „Meine Beiträge“. Gespeichert bleibt er trotzdem, ' +
    'und zurückholen kannst du ihn nicht. Macht er dich erkennbar, entfernen wir ihn auf deinen Hinweis ganz ' +
    '(siehe Datenschutz).',
  ja: 'Löschen',
  nein: 'Abbrechen',
};

/**
 * Was beim Loeschen schiefging. 401 behandelt der Auth-Interceptor (Anmeldung); 403
 * heisst, der Beitrag ist nicht der eigene, und "noch einmal" waere ein falscher Rat.
 */
export function loeschenFehlertext(status: number | undefined): string {
  if (status === 403) {
    return 'Löschen kann nur der Autor des Beitrags.';
  }
  return 'Löschen hat nicht geklappt. Versuch es gleich noch einmal.';
}

/**
 * Den eigenen Beitrag aendern (#299) und loeschen (#250), mit Dialog, Rueckfrage und
 * Meldung: fuer das Sheet und fuer die Karten im Album von „Meine Beiträge“, die beide
 * dasselbe anbieten.
 */
@Injectable({ providedIn: 'root' })
export class BeitragVerwaltenService {
  constructor(
    private dialog: MatDialog,
    private snackBar: MatSnackBar,
    private beitraege: MeineBeitraegeService,
  ) {}

  /** Der Dialog fuer Titel, Text und Herkunft; true, wenn gespeichert ist. */
  aendern(daten: KartenDaten): Observable<boolean> {
    return this.dialog
      .open(BeitragAendernDialogComponent, { data: daten, width: '560px', maxWidth: '95vw' })
      .afterClosed()
      .pipe(
        map((gespeichert) => gespeichert === true),
        tap((gespeichert) => {
          if (gespeichert) {
            this.snackBar.open('Beitrag geändert', 'OK', { duration: 3000 });
          }
        }),
      );
  }

  /**
   * Nach der Rueckfrage loeschen; true, wenn der Beitrag fuer die Liste weg ist:
   * geloescht oder schon nicht mehr da (404, geloescht oder gesperrt). Abbrechen
   * liefert nichts, ein Fehler false und eine Meldung.
   */
  loeschen(id: string): Observable<boolean> {
    return this.dialog
      .open(BestaetigungsDialogComponent, { data: LOESCHEN_FRAGE, autoFocus: 'dialog' })
      .afterClosed()
      .pipe(
        switchMap((ja) => (ja === true ? this.beitraege.beitragLoeschen(id).pipe(map(() => 'Beitrag gelöscht')) : EMPTY)),
        catchError((fehler) => {
          if (fehler?.status === 404) {
            return of('Der Beitrag ist nicht mehr da.');
          }
          this.snackBar.open(loeschenFehlertext(fehler?.status), 'OK', { duration: 5000 });
          return of(null);
        }),
        map((meldung) => {
          if (meldung === null) {
            return false;
          }
          this.snackBar.open(meldung, 'OK', { duration: 3000 });
          return true;
        }),
      );
  }
}
