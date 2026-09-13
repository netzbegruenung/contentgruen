import { Injectable } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

import { RawInputService } from '../services/raw-input.service';
import { LoggingService } from '../services/logging.service';
import { trackingParameterEntfernen } from '../shared/url-bereinigen';

/** Query-Parameter, mit dem die Destillier-Ansicht ein Beitragsformular oeffnet. */
export const ROHINPUT_PARAM = 'rohinput';

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

  /** Die Einwurf-ID aus der Adresse, oder null ausserhalb des Ablaufs. */
  rohinputId(route: ActivatedRoute): string | null {
    return route.snapshot?.queryParamMap?.get(ROHINPUT_PARAM) ?? null;
  }

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
   * Scheitert das Markieren, ist der Beitrag trotzdem da. Der Einwurf bleibt
   * dann offen und wird nicht automatisch wieder angeboten (er hat einen eigenen
   * Entwurf) - im Fangkorb ist er weiter antippbar.
   */
  nachSpeichern(rohinputId: string, contentId: string): void {
    this.rawInputService.updateStatus(rohinputId, 'processed', contentId).subscribe({
      next: () => {
        this.snackBar.open('Gespeichert. Weiter mit dem nächsten Einwurf.', undefined, {
          duration: 4000,
          panelClass: ['success-snackbar'],
        });
        this.zumNaechsten(rohinputId);
      },
      error: (error) => {
        this.logger.error('Einwurf konnte nicht als verarbeitet markiert werden', error);
        this.snackBar.open(
          'Dein Beitrag ist gespeichert, aber der Einwurf konnte nicht als verarbeitet markiert werden.',
          'OK',
          { duration: 8000 },
        );
        this.zumNaechsten(rohinputId);
      },
    });
  }

  /** Den naechsten offenen Einwurf oeffnen; ``nach`` wird dabei uebersprungen. */
  zumNaechsten(nach: string): void {
    this.router.navigate(['/destillieren'], { queryParams: { nach } });
  }

  zurueckZumEinwurf(rohinputId: string): void {
    this.router.navigate(['/destillieren', rohinputId]);
  }
}
