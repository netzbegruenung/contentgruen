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
}

/**
 * Hier gepflegt, damit Formular und spaetere Stellen nicht auseinanderlaufen.
 * Bild hat (noch) keine.
 */
export const FORMULAR_HILFE: Partial<Record<FormularTyp, FormularHilfe>> = {
  commentary: {
    zeile: 'Deine eigenen Worte – so, dass auch eine unentschiedene Nachbarin mitgeht.',
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
  },
  generictext: {
    zeile: 'Fakten, Zahlen oder Kontext – am besten mit Herkunft.',
    frage: 'Was ist eine Hintergrundinfo?',
    antwort: 'Fakten, Zahlen oder Kontext, die eine Antwort stützen.',
    ist: ['Überprüfbar, mit Herkunft', 'Knapp: eine Zahl, ein Zusammenhang'],
    istNicht: ['Meinung ohne Beleg (→ Kommentar)', 'Fremde Texte übernehmen – in eigenen Worten zusammenfassen (CC0)'],
  },
};
