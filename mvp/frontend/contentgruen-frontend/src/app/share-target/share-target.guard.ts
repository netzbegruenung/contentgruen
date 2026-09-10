import { Injectable } from '@angular/core';
import { ActivatedRouteSnapshot, CanActivate, Router, UrlTree } from '@angular/router';
import { urlsInTextBereinigen } from '../shared/url-bereinigen';

/**
 * Nimmt die Daten aus dem Android-Teilen-Menue entgegen und leitet ins
 * Einwurf-Formular weiter.
 *
 * Ein Guard und keine Komponente, weil es keine Zwischenseite geben soll: der
 * Guard laeuft, bevor irgendetwas gerendert wird, legt die Daten ab und liefert
 * direkt einen UrlTree auf /einwerfen. Sichtbar ist fuer die teilende Person nur
 * das Formular -- mit vorbefuelltem Feld und einem Tastendruck bis "Einwerfen".
 *
 * Der Login-Zwang steht bewusst nicht hier, sondern bleibt der AuthGuard an
 * /einwerfen. Weil die Nutzlast im sessionStorage liegt und nicht in der Adresse,
 * ueberlebt sie den Umweg ueber /login von selbst: der returnUrl muss nur nach
 * /einwerfen zuruueckfinden, nicht die geteilten Daten mittragen.
 */

/** Schluessel im sessionStorage. Bewusst mit Praefix, der Storage ist geteilt. */
export const SHARE_EINWURF_SCHLUESSEL = 'contentgruen.share.einwurf';

/** Was das Teilen-Menue liefert -- alle drei Felder sind optional. */
export interface ShareDaten {
  title?: string | null;
  text?: string | null;
  url?: string | null;
}

/**
 * Baut aus den geteilten Feldern den Text fuer das Einwurf-Feld.
 *
 * Der Geraete-Test hat gezeigt, dass beide Quellen die Adresse im
 * ``text``-Parameter liefern und nie in ``url`` -- Chrome legt zusaetzlich einen
 * ``title`` bei, Instagram nicht. ``url`` wird trotzdem beruecksichtigt, weil das
 * Manifest den Parameter anmeldet und andere Apps ihn benutzen koennen; doppelt
 * taucht die Adresse dabei nicht auf.
 *
 * Der Titel kommt in die erste Zeile: ``einwurfZerlegen`` im Formular zieht die
 * Adresse selbst heraus und legt den ganzen Text als ``content`` ab -- genau die
 * gewuenschte Aufteilung, ohne dass hier etwas ueber das Datenmodell wissen muss.
 */
export function einwurfAusShareDaten(daten: ShareDaten): string {
  const text = urlsInTextBereinigen((daten.text ?? '').trim());
  const url = urlsInTextBereinigen((daten.url ?? '').trim());
  const titel = (daten.title ?? '').trim();

  const zeilen: string[] = [];
  if (titel) {
    zeilen.push(titel);
  }
  if (text) {
    zeilen.push(text);
  }
  // Nur, wenn die Adresse nicht ohnehin schon im Text steht.
  if (url && !text.includes(url)) {
    zeilen.push(url);
  }

  return zeilen.join('\n');
}

@Injectable({ providedIn: 'root' })
export class ShareTargetGuard implements CanActivate {
  constructor(private router: Router) {}

  canActivate(route: ActivatedRouteSnapshot): boolean | UrlTree {
    // Die Diagnose-Ansicht aus Schritt 0 bleibt erreichbar, aber nur ausdruecklich.
    // Sie hat den Instagram-Fall belegt und ist der Weg, das erneut zu tun, wenn
    // sich das Verhalten einer App aendert.
    if (route.queryParamMap.has('debug')) {
      return true;
    }

    const einwurf = einwurfAusShareDaten({
      title: route.queryParamMap.get('title'),
      text: route.queryParamMap.get('text'),
      url: route.queryParamMap.get('url'),
    });

    if (einwurf) {
      this.ablegen(einwurf);
    }

    return this.router.parseUrl('/einwerfen');
  }

  /**
   * sessionStorage ist im privaten Modus und bei blockierten Seitendaten nicht
   * beschreibbar und wirft dann. Das darf den Weg ins Formular nicht abbrechen --
   * schlimmstenfalls steht dort ein leeres Feld statt eines vorbefuellten.
   */
  private ablegen(einwurf: string): void {
    try {
      sessionStorage.setItem(SHARE_EINWURF_SCHLUESSEL, einwurf);
    } catch {
      // Absichtlich still: siehe oben.
    }
  }
}
