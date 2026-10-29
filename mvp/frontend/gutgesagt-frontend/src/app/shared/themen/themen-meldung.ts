import { Thema } from '../../services/dtos/themenDtos';

/**
 * Die Saetze, mit denen die Seiten sagen, welche Themen eine Aussage nach dem Anlegen
 * hat - „Hier fehlt eine Antwort“ nach dem Vorab-Anlegen und die Seite „Gespeichert“
 * nach einem Beitrag mit neuer Aussage (#455). Eine Formulierung fuer beide.
 */
export const THEMEN_NICHT_GESPEICHERT = 'Die Themen konnten nicht gespeichert werden.';

export function aussageGibtEsSchon(text: string): string {
  return `Diese Aussage gibt es schon: „${text}“`;
}

export function ihreThemen(themen: Thema[]): string {
  return `Ihre Themen: ${themen.map((t) => t.name).join(', ')}.`;
}

/**
 * Was nach dem Speichern eines Beitrags zu den gewaehlten Themen zu sagen ist; null,
 * wenn nichts. Die Aussage hat dieselben, wenn sie neu war oder noch keine hatte. Hat
 * sie andere, gab es sie schon mit Themen, und die behielt sie; hat sie keine,
 * scheiterte das Zuordnen.
 */
export function themenHinweis(gewaehlt: string[], aussageText: string, themen: Thema[]): string | null {
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
  return `${aussageGibtEsSchon(aussageText)} ${ihreThemen(themen)}`;
}
