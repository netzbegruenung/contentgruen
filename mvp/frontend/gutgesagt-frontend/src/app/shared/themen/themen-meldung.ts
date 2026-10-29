import { Thema } from '../../services/dtos/themenDtos';

/**
 * Die Saetze, mit denen die Seiten sagen, welche Themen eine Aussage nach dem Anlegen
 * hat - „Hier fehlt eine Antwort“ nach dem Vorab-Anlegen und die Seite „Gespeichert“
 * nach einem Beitrag mit neuer Aussage (#455). Eine Formulierung fuer beide.
 */
export const THEMEN_NICHT_GESPEICHERT = 'Themen nicht gespeichert.';

export const AUSSAGE_GIBT_ES_SCHON = 'Diese Aussage gibt es schon.';

/** Die Themen der Aussage, auch bei einem „Themen:“. */
export function themenDerAussage(themen: Thema[]): string {
  return `Themen: ${themen.map((t) => t.name).join(', ')}.`;
}

/**
 * Was nach dem Speichern eines Beitrags zu den gewaehlten Themen zu sagen ist; null,
 * wenn nichts. Die Aussage hat dieselben, wenn sie neu war oder noch keine hatte. Hat
 * sie andere, gab es sie schon mit Themen, und die behielt sie; hat sie keine,
 * scheiterte das Zuordnen.
 */
export function themenHinweis(gewaehlt: string[], themen: Thema[]): string | null {
  if (gewaehlt.length === 0) {
    return null;
  }
  if (themen.length === 0) {
    return THEMEN_NICHT_GESPEICHERT;
  }
  const jetzt = new Set(themen.map((t) => t.schluessel));
  if (jetzt.size === gewaehlt.length && gewaehlt.every((s) => jetzt.has(s))) {
    return null;
  }
  return `${AUSSAGE_GIBT_ES_SCHON} ${themenDerAussage(themen)}`;
}
