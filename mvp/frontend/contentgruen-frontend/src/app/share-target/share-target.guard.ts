import { Injectable } from '@angular/core';
import { ActivatedRouteSnapshot, CanActivate, Router, UrlTree } from '@angular/router';
import { ersteAdresse, urlsInTextBereinigen } from '../shared/url-bereinigen';

/**
 * Nimmt die Daten aus dem Android-Teilen-Menue entgegen und leitet ins
 * Einwurf-Formular weiter.
 *
 * Ein Guard und keine Komponente, weil es keine Zwischenseite geben soll: der
 * Guard laeuft, bevor irgendetwas gerendert wird, legt die Daten ab und liefert
 * direkt einen UrlTree auf /einwerfen. Sichtbar ist fuer die teilende Person nur
 * das Formular -- mit vorbefuellten Feldern und einem Tastendruck bis "Einwerfen".
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

/** Der geteilte Einwurf, schon nach den Feldern des Formulars getrennt. */
export interface GeteilterEinwurf {
  /** Die Adresse aus url, sonst die erste aus text, ohne Tracking-Parameter. Wird der Link. */
  url: string | null;
  /** Der Seitentitel. Chrome schickt einen mit, Instagram nicht. Nur ein Vorschlag. */
  titel: string | null;
  /** Was im text-Parameter ausser der Adresse noch stand. Nur ein Vorschlag. */
  text: string | null;
}

/**
 * Trennt die geteilten Felder in Link und Vorschlaege fuer den Hinweis.
 *
 * Der Geraete-Test hat gezeigt, dass beide Quellen die Adresse im
 * ``text``-Parameter liefern und nie in ``url`` -- Chrome legt zusaetzlich einen
 * ``title`` bei, Instagram nicht. ``url`` wird trotzdem beruecksichtigt, weil das
 * Manifest den Parameter anmeldet und andere Apps ihn benutzen koennen.
 *
 * Titel und uebriger Text sind nichts, was die teilende Person geschrieben hat.
 * Das Formular zeigt sie deshalb nur als markierte, loeschbare Vorbelegung.
 */
export function einwurfAusShareDaten(daten: ShareDaten): GeteilterEinwurf {
  const text = urlsInTextBereinigen((daten.text ?? '').trim());
  const urlParameter = urlsInTextBereinigen((daten.url ?? '').trim());
  const titel = (daten.title ?? '').trim();

  // Schickt eine App eine andere Adresse in url als im Text, ist url der Link und
  // die Adresse im Text bleibt Teil des Hinweises - verloren geht keine von beiden.
  const url = ersteAdresse(urlParameter) ?? ersteAdresse(text);
  const ohneAdresse = url ? text.split(url).join(' ') : text;
  const rest = ohneAdresse
    .replace(/[ \t]+/g, ' ')
    .replace(/ *\n */g, '\n')
    .trim();

  return {
    url,
    titel: titel || null,
    text: rest && rest !== titel ? rest : null,
  };
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

    if (einwurf.url || einwurf.titel || einwurf.text) {
      this.ablegen(einwurf);
    }

    return this.router.parseUrl('/einwerfen');
  }

  /**
   * sessionStorage ist im privaten Modus und bei blockierten Seitendaten nicht
   * beschreibbar und wirft dann. Das darf den Weg ins Formular nicht abbrechen --
   * schlimmstenfalls steht dort ein leeres Formular statt eines vorbefuellten.
   */
  private ablegen(einwurf: GeteilterEinwurf): void {
    try {
      sessionStorage.setItem(SHARE_EINWURF_SCHLUESSEL, JSON.stringify(einwurf));
    } catch {
      // Absichtlich still: siehe oben.
    }
  }
}
