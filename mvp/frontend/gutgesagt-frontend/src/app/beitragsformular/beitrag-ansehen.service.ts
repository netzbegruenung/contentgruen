import { Injectable } from '@angular/core';
import { MatBottomSheet } from '@angular/material/bottom-sheet';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

import { BeitragSheetComponent } from '../beitragskarte/beitrag-sheet.component';
import { KartenDaten, ausSuchergebnis } from '../beitragskarte/karten-daten';
import { CommentaryService } from '../services/commentary.service';
import { GenericTextService } from '../services/generic-text.service';
import { LoggingService } from '../services/logging.service';
import { resolveContentType } from '../shared/content-type-registry';

/**
 * Einen gespeicherten Beitrag als volle Karte im Bottom Sheet zeigen - fuer Hinweise
 * wie "Es gibt schon einen sehr aehnlichen Kommentar" oder "Aus diesem Einwurf ist
 * schon ein Beitrag entstanden". Kommentar und Hintergrundinfo; andere Typen nicht.
 */
@Injectable({ providedIn: 'root' })
export class BeitragAnsehenService {
  constructor(
    private commentaryService: CommentaryService,
    private genericTextService: GenericTextService,
    private bottomSheet: MatBottomSheet,
    private snackBar: MatSnackBar,
    private logger: LoggingService,
  ) {}

  /** Laesst sich ein Beitrag dieses Typs hier zeigen? Beide Schreibweisen (generic_text, generictext). */
  kannAnsehen(contentType: string | null | undefined): boolean {
    const typ = resolveContentType(contentType);
    return typ === 'commentary' || typ === 'generictext';
  }

  oeffnen(id: string, contentType: string | null | undefined): void {
    const karte$ = this.laden(id, resolveContentType(contentType));
    if (!karte$) {
      return;
    }
    karte$.subscribe({
      next: (karte) =>
        this.bottomSheet.open(BeitragSheetComponent, { data: karte, ariaLabel: karte.titel || 'Beitrag' }),
      error: (fehler) => {
        this.logger.warn('Beitrag zum Ansehen nicht ladbar', fehler);
        this.snackBar.open('Der Beitrag lässt sich gerade nicht anzeigen.', 'OK', { duration: 5000 });
      },
    });
  }

  private laden(id: string, typ: string | undefined): Observable<KartenDaten> | null {
    if (typ === 'commentary') {
      return this.commentaryService
        .getCommentaryById(id)
        .pipe(map((inhalt) => ausSuchergebnis({ commentary_result: inhalt, score: 1 } as any)));
    }
    if (typ === 'generictext') {
      return this.genericTextService
        .getGenericTextById(id)
        .pipe(map((inhalt) => ausSuchergebnis({ generictext_result: inhalt, score: 1 } as any)));
    }
    return null;
  }
}
