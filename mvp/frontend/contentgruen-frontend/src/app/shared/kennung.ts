/**
 * Personen stehen im Fangkorb als Keycloak-Kennung da, bis es Anzeigenamen gibt.
 * Die Kennung ist eine UUID; zum Wiedererkennen reicht der Anfang. Vollstaendig
 * gehoert sie in den Tooltip.
 */
const KENNUNG_KURZ = 8;

export function kurzeKennung(kennung: string | null | undefined): string {
  if (!kennung) {
    return 'ohne Kennung';
  }
  return kennung.length > KENNUNG_KURZ ? kennung.slice(0, KENNUNG_KURZ) : kennung;
}
