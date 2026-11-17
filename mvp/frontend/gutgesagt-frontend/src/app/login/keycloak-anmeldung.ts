import { environment } from '../../environments/environment';
import { rueckkehrzielMerken } from './rueckkehrziel';

/**
 * Zur Anmeldung mit dem Netzbegrünung-Konto (Keycloak), danach zurück auf `ziel`. Aus der
 * Login-Auswahl und aus der Vorschau „Das erwartet dich mit Konto“.
 *
 * Das Ziel geht zweimal mit: im sessionStorage und als Parameter, denn der BFF schickt den
 * Browser nach der Anmeldung direkt dorthin, und das hängt nicht davon ab, dass der
 * sessionStorage den Umweg über Keycloak übersteht.
 */
export function keycloakAnmelden(ziel: string, fenster: Pick<Window, 'location'> = window): void {
  rueckkehrzielMerken(ziel);
  fenster.location.href = `${environment.baseUrl}/api/auth/login/keycloak?returnUrl=${encodeURIComponent(ziel)}`;
}
