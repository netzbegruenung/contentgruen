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
    zeile: 'Deine eigene Formulierung – so, dass sie eine unentschiedene Nachbarin überzeugt.',
    frage: 'Was ist ein Kommentar?',
    antwort: 'Eine Antwort, die man so posten kann.',
    ist: ['Deine eigene Formulierung', 'Überzeugt eine unentschiedene Nachbarin, nicht nur die eigenen Leute'],
    istNicht: ['Kopierte Captions oder Zitate', 'Unterstellungen, Lager-Etiketten, Häme'],
    beispiel: {
      aussage: 'Die Grünen wollen uns das Autofahren verbieten',
      antwort:
        'Niemand will dir dein Auto wegnehmen. Es geht darum, dass du auch ohne gut ankommst, wo Bus oder Rad passen.',
    },
  },
  generictext: {
    zeile: 'Fakten, Zahlen oder Kontext – am besten mit Herkunft.',
    frage: 'Was ist eine Hintergrundinfo?',
    antwort: 'Fakten, Zahlen oder Kontext, die eine Antwort stützen.',
    ist: ['Überprüfbar, mit Herkunft', 'Knapp: eine Zahl, ein Zusammenhang'],
    istNicht: ['Meinung ohne Beleg (→ Kommentar)', 'Ganze Studien oder Artikel abschreiben'],
  },
};
