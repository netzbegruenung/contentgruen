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
 * man in „Hier fehlt eine Antwort“ oder auf der Admin-Seite „Themen“. Und erst, wenn
 * der Text ausdruecklich als neue Aussage gewaehlt ist: Solange darunter noch
 * vorhandene zur Wahl stehen, kaemen „Themen der neuen Aussage“ zu frueh (#617).
 */
export function themenWaehlbar(aussage: AntwortAuf): boolean {
  return !aussage.id && !!aussage.text && aussage.neuGewaehlt === true;
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
  antwort: { themen?: Thema[] },
  verknuepft: boolean,
): { themenHinweis?: string } {
  if (!verknuepft || !anfrage.themen?.length) {
    return {};
  }
  const hinweis = themenHinweis(anfrage.themen, antwort.themen ?? []);
  return hinweis ? { themenHinweis: hinweis } : {};
}

/** Was das Backend nach dem Speichern zur Aussage meldet (Post, Bild, #619; wie Hintergrundinfo). */
export interface AussageInAntwort {
  /** Die Aussage, an der der Beitrag jetzt haengt; fehlt ohne Aussage oder wenn das Verknuepfen scheiterte. */
  statement_id?: string | null;
  /** Ihr Text; bei Text-Anfragen kann das eine schon vorhandene, aehnliche Aussage sein. */
  statement_text?: string | null;
  themen?: Thema[];
  /** false: Aussage angegeben, aber nicht verknuepft - der Beitrag steht trotzdem. */
  verknuepft?: boolean;
}

/**
 * Das Ergebnis fuer die Ergebnisseite. Wurde eine Aussage mitgeschickt, gilt sie nur
 * als verknuepft, wenn das Backend es bestaetigt; dann ist es die tatsaechlich
 * verknuepfte Aussage. Sonst bleibt die eingegebene stehen, damit die Seite sagen kann,
 * woran es nicht haengt.
 */
export function alsGespeichert(
  id: string,
  eingegeben: AntwortAuf,
  anfrage: AussageInAnfrage,
  antwort: AussageInAntwort,
): { id: string; aussage: AntwortAuf; verknuepft: boolean; themenHinweis?: string } {
  const aussageGeschickt = !!(anfrage.statement_id || anfrage.statement_text);
  const verknuepft = !aussageGeschickt || antwort.verknuepft === true;
  const aussage =
    aussageGeschickt && verknuepft && antwort.statement_id
      ? { id: antwort.statement_id, text: antwort.statement_text ?? eingegeben.text }
      : eingegeben;
  return { id, aussage, verknuepft, ...themenHinweisNachSpeichern(anfrage, antwort, verknuepft) };
}
