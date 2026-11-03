/**
 * Was Kommentar- und Hintergrundinfo-Formular zur Dublette teilen (Glossar
 * "Dublette"): der vorhandene Beitrag aus der Antwort, der Zustand der Entscheidung
 * und der Hinweis dazu. Die Texte unterscheiden sich nur im Genus und kommen je
 * Beitragstyp als `DublettenTexte`.
 */

import type { VorhandenDto } from '../../services/dtos/dubletteDtos';

/**
 * Ein schon vorhandener, sehr aehnlicher Beitrag - der eigene waere seine Dublette.
 * Angelegt wurde nichts; die Person entscheidet.
 */
export interface Vorhanden<Anfrage> {
  id: string;
  /** Titel, soweit das Backend ihn nennt. */
  titel: string | null;
  /** Von derselben Person: Zustimmen sagt dann nichts, nehmen schon. */
  eigen: boolean;
  /** Text der Aussage, mit der er nach dem Nehmen verknuepft ist; sonst null. */
  aussage: string | null;
  /** Die Anfrage, die ihn gefunden hat; Nehmen schickt sie mit vorhanden_nehmen noch einmal. */
  anfrage: Anfrage;
  /** Wie die Person ihn gewaehlt hat; null, solange sie nicht entschieden hat. */
  gewaehlt: 'zugestimmt' | 'genommen' | null;
}

/** Die Hinweise zur Dublette eines Beitragstyps. */
export interface DublettenTexte {
  /** Es gibt schon einen sehr aehnlichen Beitrag. */
  hinweis: string;
  /** ... von jemand anderem: der wird nicht mit der eigenen Aussage verknuepft. */
  fremdHinweis: string;
  /** ... die Absicht geht nicht verloren, nur ueber einen anderen Weg. */
  fremdZuordnen: string;
  /** Nach dem Zustimmen: Die Stimme ist gezaehlt, gespeichert wurde nichts. */
  zugestimmt: string;
  /** Der eigene vorhandene ist gewaehlt, ohne Aussage: keine Stimme, gespeichert wurde nichts. */
  genommen: string;
  /** Der genommene vorhandene haengt jetzt auch an dieser Aussage. */
  verknuepft: (aussage: string) => string;
}

/**
 * Der vorhandene aus der Antwort, noch ohne Entscheidung; null ohne Dublette. Gemerkt
 * wird die Anfrage ohne die Entscheidung, die sie gebracht hat - ueber diesen
 * vorhandenen hat die Person noch nicht entschieden.
 */
export function vorhandenAus<Anfrage extends { trotz_dublette_von?: string; vorhanden_nehmen?: string }>(
  anfrage: Anfrage,
  antwort: { id: string; vorhanden?: VorhandenDto | null },
): Vorhanden<Omit<Anfrage, 'trotz_dublette_von' | 'vorhanden_nehmen'>> | null {
  if (!antwort.vorhanden) {
    return null;
  }
  const { trotz_dublette_von, vorhanden_nehmen, ...ohneEntscheidung } = anfrage;
  return {
    id: antwort.id,
    titel: antwort.vorhanden.titel ?? null,
    eigen: antwort.vorhanden.eigen === true,
    aussage: null,
    anfrage: ohneEntscheidung,
    gewaehlt: null,
  };
}

/**
 * Der Hinweis zur Dublette: nach der Wahl, was gilt; davor, ob es einen gibt und -
 * wenn er fremd ist und eine Aussage mitkam -, dass er sich ihr spaeter zuordnen laesst.
 */
export function dublettenHinweis(
  vorhanden: Vorhanden<unknown> | null,
  texte: DublettenTexte,
  mitAussage: boolean,
): string {
  if (vorhanden?.gewaehlt === 'zugestimmt') {
    return texte.zugestimmt;
  }
  if (vorhanden?.gewaehlt === 'genommen') {
    return vorhanden.aussage ? texte.verknuepft(vorhanden.aussage) : texte.genommen;
  }
  return vorhanden && !vorhanden.eigen && mitAussage ? `${texte.fremdHinweis} ${texte.fremdZuordnen}` : texte.hinweis;
}
