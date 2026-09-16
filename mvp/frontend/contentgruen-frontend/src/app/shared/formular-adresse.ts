import { Params } from '@angular/router';

/**
 * Die Beitragsformulare: je Typ eine eigene Seite, auf Desktop und Handy gleich.
 * /contribute ist nur die Uebersicht davor und bettet kein Formular ein.
 */
export type FormularTyp = 'commentary' | 'generictext' | 'image';

export const FORMULAR_PFAD: Record<FormularTyp, string> = {
  commentary: '/workflow/add-commentary',
  generictext: '/workflow/add-generictext',
  image: '/workflow/add-image',
};

/** Query-Parameter mit der ID der Aussage, auf die der Beitrag antwortet. */
export const AUSSAGE_PARAM = 'aussage';

/**
 * Query-Parameter mit dem Text der Aussage, wenn keine ID bekannt ist. Das
 * Formular legt dafuer beim Oeffnen nichts an; aufgeloest wird erst beim Speichern.
 */
export const SUCHTEXT_PARAM = 'searchQuery';

export function istFormularTyp(wert: string | null | undefined): wert is FormularTyp {
  return !!wert && Object.prototype.hasOwnProperty.call(FORMULAR_PFAD, wert);
}

/**
 * Nur eine echte UUID taugt als Aussage. Das Backend schreibt eine
 * fehlgeschlagene Anlage in der Suche als "None" in die Antwort (str(None)).
 */
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * Query-Parameter fuer ein Formular, das auf eine Aussage antwortet: die ID, wo
 * es eine gibt, sonst der Text. Ohne beides bleiben sie leer.
 */
export function aussageParameter(aussageId: string | null | undefined, text: string | null | undefined): Params {
  if (aussageId && UUID.test(aussageId)) {
    return { [AUSSAGE_PARAM]: aussageId };
  }
  const suchtext = text?.trim();
  return suchtext ? { [SUCHTEXT_PARAM]: suchtext } : {};
}
