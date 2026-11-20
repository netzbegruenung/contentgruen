import { environment } from '../../environments/environment';
import { rueckkehrzielMerken } from './rueckkehrziel';

/**
 * Anmeldeweg über den Realm: `netzbegruenung` springt über dessen Anmeldeseite gleich zur
 * Netzbegrünung (der BFF schickt dann `kc_idp_hint` mit); ohne Weg zeigt Keycloak die Seite
 * mit E-Mail und Passwort für Einladungskonten und dem Knopf zur Netzbegrünung.
 */
export type KeycloakWeg = 'netzbegruenung';

/**
 * Zur Anmeldung über den Realm (Keycloak), danach zurück auf `ziel`. Aus der Login-Auswahl,
 * der Vorschau „Das erwartet dich mit Konto“ und dem Einlösen einer Einladung.
 *
 * Das Ziel geht zweimal mit: im sessionStorage und als Parameter, denn der BFF schickt den
 * Browser nach der Anmeldung direkt dorthin, und das hängt nicht davon ab, dass der
 * sessionStorage den Umweg über Keycloak übersteht.
 */
export function keycloakAnmelden(
  ziel: string,
  fenster: Pick<Window, 'location'> = window,
  weg: KeycloakWeg | null = null,
): void {
  rueckkehrzielMerken(ziel);
  const wegParameter = weg ? `weg=${weg}&` : '';
  fenster.location.href = `${environment.baseUrl}/api/auth/login/keycloak?${wegParameter}returnUrl=${encodeURIComponent(ziel)}`;
}
