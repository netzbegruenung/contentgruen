/**
 * Die kurze Erklärung, die sich beim Antippen des Siegels auf einer Karte öffnet (#427):
 * wie die Güte zustande kommt. Genannt werden nur die erfüllten Kriterien; was das
 * Gegenlesen anmerkt, sieht allein die schreibende Person im Formular (#358), auf der
 * Karte stünde es wie ein Pranger.
 */
import type { Anmerkung } from '../../../beitragsformular/gegenlesen/gegenlesen.service';
import { HOECHSTE_GUETE, normierteGuete } from './siegel-zeichnung';

/** Ein erfülltes Kriterium, positiv gesagt; je Art des Gegenlesens. */
export const KRITERIUM_ERFUELLT: Record<Anmerkung['art'], string> = {
  verneinung: 'Beginnt ohne Verneinung',
  schluesselwoerter: 'Setzt eigene Begriffe',
  satzlaenge: 'Kurze Sätze',
  statt_sag: 'Ohne Wörter aus der Liste „statt X, sag Y“',
  passiv: 'Aktiv formuliert',
  kompositum: 'Ohne lange zusammengesetzte Wörter',
  gedankenstrich: 'Ohne Gedankenstriche',
  parteistimme: 'Klingt nach Nachbarin, nicht nach Partei',
  titel_frage: 'Titel als Behauptung, nicht als Frage',
  // Prüft nur das Formular, das die Herkunft kennt; auf der Karte nie erfüllt gemeldet.
  zahl_ohne_herkunft: 'Zahlen mit Herkunft',
};

export interface SiegelErklaerung {
  ueberschrift: string;
  kriterien: string[];
  stimmen: string;
}

export function siegelErklaerung(guete: number | null, erfuellt: string[], stimmenZaehlen: boolean): SiegelErklaerung {
  const g = normierteGuete(guete);
  return {
    ueberschrift: g === null ? 'Neu: noch keine Güte' : `Güte ${g} von ${HOECHSTE_GUETE}`,
    kriterien: erfuellt
      .filter((art): art is Anmerkung['art'] => Object.hasOwn(KRITERIUM_ERFUELLT, art))
      .map((art) => KRITERIUM_ERFUELLT[art]),
    stimmen: stimmenZaehlen
      ? 'Die Stimmen anderer sind eingerechnet. Je mehr Menschen bewerten, desto mehr zählt ihr Urteil.'
      : 'Die Stimmen anderer zählen, sobald genug zusammenkommen. Dann wiegt ihr Urteil immer mehr.',
  };
}
