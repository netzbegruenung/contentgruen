import { Injectable } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';

import { BeitragsTyp, EinwurfService } from '../services/einwurf.service';
import { LoggingService } from '../services/logging.service';
import { FangkorbTab } from '../raw-input-list/fangkorb-filter';
import { trackingParameterEntfernen } from '../shared/url-bereinigen';
import { KartenDaten, ausEinwurf } from '../beitragskarte/karten-daten';

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
  /** Der eigene Satz - er wird der Titel. */
  titel: string;
  /** Der Link des Einwurfs, ohne Tracking-Parameter - er wird die Herkunft. */
  url: string | null;
  /** Der Einwurf als Kopf ueber dem Formular: Sandband, Link, der Satz. */
  kopf?: KartenDaten;
}

/**
 * Die Naht zwischen Destillier-Ansicht und Beitragsformular.
 *
 * In der Adresse steht nur die ID des Einwurfs (?rohinput=...). Satz und Link
 * holt das Formular vom Server, damit ein PWA-Neustart nichts verliert und kein
 * Freitext in der Adresse landet. Nach dem Speichern wird der Einwurf als
 * ausformuliert markiert; den naechsten waehlt man auf der Ergebnisseite.
 */
@Injectable({ providedIn: 'root' })
export class DestillierUebergabeService {
  constructor(
    private einwurfService: EinwurfService,
    private router: Router,
    private logger: LoggingService,
  ) {}

  vorbefuellungLaden(rohinputId: string): Observable<Vorbefuellung> {
    return this.einwurfService.einwurfLaden(rohinputId).pipe(
      map((einwurf) => {
        const karte = ausEinwurf(einwurf);
        const titel = einwurf.own_draft ?? '';
        return {
          rohinputId: einwurf.id,
          titel,
          url: einwurf.url ? trackingParameterEntfernen(einwurf.url) : null,
          kopf: karte.einwurfAngaben ? { ...karte, einwurfAngaben: { ...karte.einwurfAngaben, kopfSatz: titel || undefined } } : karte,
        };
      }),
    );
  }

  /**
   * Der Beitrag ist gespeichert: Einwurf als ausformuliert markieren, ohne weiterzuspringen.
   *
   * Fuer Formulare mit Ergebnisseite - dort waehlt man selbst den naechsten
   * Einwurf. Liefert, ob das Markieren geklappt hat; ein Fehler bricht nichts ab,
   * der Beitrag ist ja da.
   */
  mitBeitragVerknuepfen(rohinputId: string, contentId: string, typ: BeitragsTyp): Observable<boolean> {
    return this.einwurfService.updateStatus(rohinputId, 'processed', contentId, typ).pipe(
      map(() => true),
      catchError((error) => {
        this.logger.error('Einwurf konnte nicht als ausformuliert markiert werden', error);
        return of(false);
      }),
    );
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
}
