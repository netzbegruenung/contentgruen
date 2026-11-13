import { ActivatedRouteSnapshot } from '@angular/router';

import { EINWURF_PARAM } from '../../destillieren/einwurf-adresse';
import { ROUTES } from '../../shared/constants/app.constants';

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

/**
 * ?von=hier-fehlt-eine-antwort: Das Formular kam ueber "Antworten" von
 * "Hier fehlt eine Antwort". Es gilt nicht als aus der Suche (sonst zeigte die
 * Ergebnisseite die letzte, fremde Suchanfrage), und die Pfeile fuehren dorthin zurueck.
 */
export const VON_HIER_FEHLT_EINE_ANTWORT = 'hier-fehlt-eine-antwort';

export function vonHierFehltEineAntwort(params: { get(name: string): string | null }): boolean {
  return params.get(VON_PARAM) === VON_HIER_FEHLT_EINE_ANTWORT;
}

/**
 * ?gesucht=<N>: Wie viele Personen ohne Treffer nach der Aussage gesucht haben, wie
 * "Hier fehlt eine Antwort" sie zeigt. Reist von dort ueber das Formular auf die
 * Ergebnisseite mit, die damit "Luecke zu" sagt; die Zahl steht auf der Herkunftsseite
 * schon offen, ein neuer Abruf entsteht nicht.
 */
export const GESUCHT_PARAM = 'gesucht';

/** Die Zahl aus ?gesucht=; 0 ohne Angabe oder bei Unsinn. */
export function gesuchtAus(params: { get(name: string): string | null }): number {
  const zahl = Number.parseInt(params.get(GESUCHT_PARAM) ?? '', 10);
  return Number.isFinite(zahl) && zahl > 0 ? zahl : 0;
}

/** Der Satz unter "Luecke zu.", je nachdem, wie viele Personen gesucht haben. */
export function lueckeZuSatz(personen: number): string {
  if (personen <= 0) {
    return 'Wer danach sucht, findet ab jetzt deine Antwort.';
  }
  return personen === 1
    ? 'Eine Person hat danach gesucht, ab jetzt findet sie was.'
    : `${personen} Personen haben danach gesucht, ab jetzt finden sie was.`;
}

export type Herkunft = 'fangkorb' | 'suche' | 'frei';

/** Was ein Beitragsformular nach dem Speichern meldet; die Ergebnisseite zeigt es. */
export interface BeitragGespeichert {
  id: string;
  aussage: { id: string; text: string };
  /** false: Aussage angegeben, aber nicht verknuepft - der Beitrag steht trotzdem. */
  verknuepft: boolean;
  /** Die Aussage wurde beim Speichern neu angelegt (laut Server, #617); fehlt sonst. */
  aussageNeu?: boolean;
  /** Die gewaehlten Themen galten nicht (themenHinweisNachSpeichern); fehlt sonst. */
  themenHinweis?: string;
}

export interface GespeichertZustand {
  /** Die Aussage, auf die der Beitrag antwortet; fehlt ohne Aussage. */
  aussage?: { id: string; text: string };
  /** false: Aussage angegeben, aber nicht verknuepft. */
  verknuepft?: boolean;
  /** Die Aussage wurde beim Speichern neu angelegt: Marke "neu" an "Antwort auf" (#617). */
  aussageNeu?: boolean;
  /** Die gewaehlten Themen der neuen Aussage galten nicht: der Satz dazu (#455). */
  themenHinweis?: string;
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
      return vonHierFehltEineAntwort(params) ? ROUTES.HIER_FEHLT_EINE_ANTWORT : '/contribute';
  }
}
