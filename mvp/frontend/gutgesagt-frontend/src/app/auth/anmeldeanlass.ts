/**
 * Rueckkehrziel-Parameter: Wozu jemand sich angemeldet hat, wenn es dafuer nach der
 * Rueckkehr einen Satz gibt. Steht nur im Rueckkehrziel (AuthService.login) und
 * verschwindet nach der Rueckkehr wieder aus der Adresse.
 */
export const ANLASS_PARAM = 'anlass';

export type Anmeldeanlass = 'abstimmen';

/** Der Satz nach der Rueckkehr; die Stimme gibt die Person selbst ab, nicht die App. */
export const NACH_ANMELDUNG_HINWEIS: Record<Anmeldeanlass, string> = {
  abstimmen: 'Du bist angemeldet. Jetzt kannst du abstimmen.',
};

export function istAnlass(wert: string | null): wert is Anmeldeanlass {
  return !!wert && Object.prototype.hasOwnProperty.call(NACH_ANMELDUNG_HINWEIS, wert);
}
