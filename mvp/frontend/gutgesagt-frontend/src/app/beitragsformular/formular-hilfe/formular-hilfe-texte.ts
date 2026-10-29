import { FormularTyp } from '../../shared/formular-adresse';

/** Die Qualitaetsregeln eines Beitragstyps, oben im Formular. */
export interface FormularHilfe {
  /** Immer sichtbar, neben dem ?. */
  zeile: string;
  frage: string;
  antwort: string;
  ist: string[];
  istNicht: string[];
  beispiel?: { aussage: string; antwort: string };
  /** Zeigt die Schreibregeln und Schreibhilfen (shared/schreibregeln.ts). */
  schreibregeln?: true;
  /** Zeigt gute und schwache Titel; nur wo der Titel eine Behauptung ist. */
  titelbeispiele?: true;
}

/**
 * Hier gepflegt, damit Formular und spaetere Stellen nicht auseinanderlaufen.
 * Bild hat (noch) keine.
 */
export const FORMULAR_HILFE: Partial<Record<FormularTyp, FormularHilfe>> = {
  commentary: {
    zeile: 'So formuliert, dass auch eine unentschiedene Nachbarin mitgeht.',
    frage: 'Was ist ein Kommentar?',
    antwort: 'Eine Antwort, die man so posten kann.',
    ist: ['Nimmt die Sorge hinter der Aussage ernst', 'Ein Punkt, konkret und alltagsnah'],
    istNicht: [
      'Fremde Texte übernehmen – du gibst deinen Text frei (CC0), das geht nur mit eigenen Worten',
      'Unterstellungen, Lager-Etiketten, Häme',
    ],
    beispiel: {
      aussage: 'Die Grünen wollen uns das Autofahren verbieten',
      antwort:
        'Wer aufs Auto angewiesen ist, soll es auch bleiben dürfen. Es geht um die anderen Wege: dass der Bus öfter fährt und das Kind sicher mit dem Rad zur Schule kommt. Dann ist auf der Straße auch mehr Platz für alle, die fahren müssen.',
    },
    schreibregeln: true,
    titelbeispiele: true,
  },
  generictext: {
    zeile: 'Knapp und überprüfbar – am besten mit Beleg.',
    frage: 'Was ist eine Hintergrundinfo?',
    antwort: 'Fakten, Zahlen oder Kontext, die eine Antwort stützen.',
    ist: ['Mit Herkunft, damit andere es nachsehen können', 'Ein Punkt: eine Zahl, ein Zusammenhang'],
    istNicht: ['Meinung ohne Beleg (→ Kommentar)', 'Fremde Texte übernehmen – in eigenen Worten zusammenfassen (CC0)'],
  },
  post: {
    zeile: 'Ein Post, den man sich zum Vorbild nehmen und teilen kann.',
    frage: 'Was ist ein Post?',
    antwort: 'Ein gelungener Beitrag aus einem sozialen Netzwerk, festgehalten mit Link.',
    ist: ['Fertig und so teilbar, wie er ist', 'Mit Link, damit andere ihn finden'],
    istNicht: [
      'Material, aus dem erst ein Beitrag werden soll (→ einwerfen)',
      'Den Post abschreiben – beschreib in eigenen Worten, worum es geht (CC0)',
    ],
    schreibregeln: true,
  },
};
