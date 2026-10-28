import { ActivatedRouteSnapshot } from '@angular/router';

import { EINWURF_PARAM } from '../../destillieren/einwurf-adresse';

/**
 * Was die Ergebnisseite nach dem Speichern wissen muss.
 *
 * Woher das Formular kam, steht in der Adresse (bleibt beim Neuladen erhalten
 * und bestimmt den Zurueck-Pfeil): ?einwurf=<id> aus dem Fangkorb, ?von=suche
 * (optional mit ?suche=<Anfrage>) aus der Suche, sonst frei. Was nur der eben
 * gespeicherte Aufruf weiss - worauf geantwortet wurde und ob die Verknuepfung
 * mit Aussage und Einwurf geklappt hat -, reist als Router-State mit und fehlt nach dem
 * Neuladen einfach.
 */
export const VON_PARAM = 'von';
export const SUCHE_PARAM = 'suche';

export type Herkunft = 'fangkorb' | 'suche' | 'frei';

/** Was ein Beitragsformular nach dem Speichern meldet; die Ergebnisseite zeigt es. */
export interface BeitragGespeichert {
  id: string;
  aussage: { id: string; text: string };
  /** false: Aussage angegeben, aber nicht verknuepft - der Beitrag steht trotzdem. */
  verknuepft: boolean;
}

export interface GespeichertZustand {
  /** Die Aussage, auf die der Beitrag antwortet; fehlt ohne Aussage. */
  aussage?: { id: string; text: string };
  /** false: Aussage angegeben, aber nicht verknuepft. */
  verknuepft?: boolean;
  /** Nur Fangkorb: false, wenn der Einwurf nicht mit dem Beitrag verknuepft wurde. */
  einwurfVerknuepft?: boolean;
}

export function herkunftAus(params: { get(name: string): string | null }): Herkunft {
  if (params.get(EINWURF_PARAM)) {
    return 'fangkorb';
  }
  return params.get(VON_PARAM) === 'suche' ? 'suche' : 'frei';
}

/** Der Zurueck-Pfeil der Ergebnisseite: dorthin, woher das Formular kam. */
export function gespeichertEltern(snapshot: ActivatedRouteSnapshot): string {
  const params = snapshot.queryParamMap;
  switch (herkunftAus(params)) {
    case 'fangkorb':
      return '/fangkorb';
    case 'suche': {
      const suche = params.get(SUCHE_PARAM);
      return suche ? `/result?searchQuery=${encodeURIComponent(suche)}` : '/search';
    }
    default:
      return '/contribute';
  }
}
