import { AntwortAuf } from './antwort-auf/antwort-auf.component';
import { Thema } from '../services/dtos/themenDtos';
import { themenHinweis } from '../shared/themen/themen-meldung';

/** Worauf ein Beitrag antwortet, wie es die Anfrage zum Speichern traegt. */
export interface AussageInAnfrage {
  statement_id?: string;
  statement_text?: string;
  themen?: string[];
}

/**
 * Themen lassen sich nur fuer eine Aussage per Text waehlen (#455): Sie entsteht erst
 * beim Speichern. Eine gewaehlte, vorhandene Aussage behaelt ihre Themen; die aendert
 * man in „Hier fehlt eine Antwort“ oder auf der Admin-Seite „Themen“.
 */
export function themenWaehlbar(aussage: AntwortAuf): boolean {
  return !aussage.id && !!aussage.text;
}

/**
 * Die gewaehlte Aussage per ID, sonst ihr Text mit den gewaehlten Themen, sonst nichts.
 * Leere Themen fehlen in der Anfrage.
 */
export function aussageFuerAnfrage(aussage: AntwortAuf, themen: string[]): AussageInAnfrage {
  if (aussage.id) {
    return { statement_id: aussage.id };
  }
  if (!aussage.text) {
    return {};
  }
  return { statement_text: aussage.text, ...(themen.length ? { themen } : {}) };
}

/**
 * Fuer die Seite „Gespeichert“: der Satz zu den gewaehlten Themen, wenn die Aussage
 * andere hat (eine vorhandene behielt ihre) oder keine (das Zuordnen scheiterte), wie
 * in „Hier fehlt eine Antwort“. Nur bei verknuepfter Aussage; sonst sagt die Seite das.
 */
export function themenHinweisNachSpeichern(
  anfrage: AussageInAnfrage,
  antwort: { statement_text?: string | null; themen?: Thema[] },
  verknuepft: boolean,
): { themenHinweis?: string } {
  if (!verknuepft || !anfrage.themen?.length) {
    return {};
  }
  const hinweis = themenHinweis(anfrage.themen, antwort.statement_text ?? anfrage.statement_text ?? '', antwort.themen ?? []);
  return hinweis ? { themenHinweis: hinweis } : {};
}
