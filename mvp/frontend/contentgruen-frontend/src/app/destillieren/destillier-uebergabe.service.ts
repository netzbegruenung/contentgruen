import { Injectable } from '@angular/core';
import { Router } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

import { BeitragsTyp, RawInputService } from '../services/raw-input.service';
import { LoggingService } from '../services/logging.service';
import { FangkorbTab } from '../raw-input-list/fangkorb-filter';
import { trackingParameterEntfernen } from '../shared/url-bereinigen';

/** Query-Parameter, mit dem die Destillier-Ansicht ein Beitragsformular oeffnet. */
export const ROHINPUT_PARAM = 'rohinput';

/**
 * Query-Parameter, mit dem die Destillier-Ansicht direkt in einem Schritt oeffnet.
 * Heute nur ``typwahl``: Der Fangkorb schickt von "Ausformulieren" dorthin.
 */
export const SCHRITT_PARAM = 'schritt';

/** Query-Parameter, der den Tab fuer den Ruecksprung in den Fangkorb traegt. */
export const TAB_PARAM = 'tab';

/** Was aus dem Einwurf ins Beitragsformular uebernommen wird. Alles bleibt aenderbar. */
export interface Vorbefuellung {
  rohinputId: string;
  /** Der eigene Entwurfssatz - er wird der Titel. */
  titel: string;
  /** Der Link des Einwurfs, ohne Tracking-Parameter - er wird die Herkunft. */
  url: string | null;
}

/**
 * Die Naht zwischen Destillier-Ansicht und Beitragsformular.
 *
 * In der Adresse steht nur die ID des Einwurfs (?rohinput=...). Satz und Link
 * holt das Formular vom Server, damit ein PWA-Neustart nichts verliert und kein
 * Freitext in der Adresse landet. Nach dem Speichern wird der Einwurf als
 * verarbeitet markiert und der naechste geoeffnet.
 */
@Injectable({ providedIn: 'root' })
export class DestillierUebergabeService {
  constructor(
    private rawInputService: RawInputService,
    private router: Router,
    private snackBar: MatSnackBar,
    private logger: LoggingService,
  ) {}

  vorbefuellungLaden(rohinputId: string): Observable<Vorbefuellung> {
    return this.rawInputService.getRawInput(rohinputId).pipe(
      map((einwurf) => ({
        rohinputId: einwurf.id,
        titel: einwurf.own_draft ?? '',
        url: einwurf.url ? trackingParameterEntfernen(einwurf.url) : null,
      })),
    );
  }

  /**
   * Der Beitrag ist gespeichert: Einwurf als verarbeitet markieren und weiter.
   *
   * Der Typ geht mit, damit die Fangkorb-Karte die Farbe des Beitrags annimmt.
   * Scheitert das Markieren, ist der Beitrag trotzdem da. Der Einwurf bleibt
   * dann destilliert und wird nicht automatisch wieder angeboten (er hat einen
   * eigenen Entwurf) - im Fangkorb ist er weiter antippbar.
   */
  nachSpeichern(rohinputId: string, contentId: string, typ: BeitragsTyp): void {
    this.rawInputService.updateStatus(rohinputId, 'processed', contentId, typ).subscribe({
      next: () => {
        this.snackBar.open('Gespeichert. Weiter mit dem nächsten Einwurf.', undefined, {
          duration: 4000,
          panelClass: ['success-snackbar'],
        });
        this.zumNaechsten(rohinputId, 'erledigt');
      },
      error: (error) => {
        this.logger.error('Einwurf konnte nicht als verarbeitet markiert werden', error);
        this.snackBar.open(
          'Dein Beitrag ist gespeichert, aber der Einwurf konnte nicht als verarbeitet markiert werden.',
          'OK',
          { duration: 8000 },
        );
        // Ohne Verknuepfung bleibt der Einwurf bei seinen Saetzen stehen - er liegt
        // also unter "Ausformulieren", nicht unter "Erledigt".
        this.zumNaechsten(rohinputId, 'ausformulieren');
      },
    });
  }

  /**
   * Den naechsten offenen Einwurf oeffnen; ``nach`` wird dabei uebersprungen.
   *
   * ``tab`` sagt, wo der Fangkorb aufgehen soll, falls keiner mehr offen ist -
   * der Tab, in dem das Ergebnis der gerade beendeten Handlung liegt. Er wird
   * durchgereicht statt geraten: Nur die Handlung selbst weiss, was sie bewirkt
   * hat.
   */
  zumNaechsten(nach: string, tab: FangkorbTab): void {
    this.router.navigate(['/destillieren'], { queryParams: { nach, [TAB_PARAM]: tab } });
  }

  zurueckZumEinwurf(rohinputId: string): void {
    this.router.navigate(['/destillieren', rohinputId]);
  }
}
