/**
 * Was Gut gesagt an KI nutzt, in einer Fassung für Über, Hilfe und Formulare (Persona-Test
 * Gerd, 13.11.2026): vorher hieß es an einer Stelle „KI schlägt höchstens etwas vor“, an
 * einer anderen „keine KI“.
 *
 * Stand im Code: Die Suche rechnet mit einem Einbettungsmodell (EMBEDDING_MODELL) und
 * einem NLI-Modell (NLI_MODELL, core/config.py), beide lokal; sie liefern Zahlen, keinen
 * Text (ADR 0005). Gegenlesen, Kürzungsvorschlag und Spracherkennung arbeiten mit festen
 * Regeln und kleinen lokalen Sprachwerkzeugen. Einen Textgenerator gibt es nicht.
 *
 * Kommt ein KI-Vorschlag (GLOSSARY, ADR 0003), stimmen diese Sätze nicht mehr: dann hier
 * ändern, die Datenschutzerklärung über ihr eigenes Ticket. Gegenlesen und
 * Kürzungsvorschlag sagen dasselbe kurz: „ohne generative KI“.
 */

/** Der Kernsatz: keine generative KI, die Beiträge schreiben Menschen. */
export const KEINE_GENERATIVE_KI = 'Gut gesagt nutzt keine generative KI: Alle Beiträge schreiben Menschen.';

/** Was die Suche stattdessen nutzt, ohne Fachbegriffe. */
export const SUCHE_MIT_SPRACHMODELLEN =
  'Die Suche vergleicht Bedeutungen mit Sprachmodellen auf unseren eigenen Servern. ' +
  'Diese Modelle schreiben keine Texte, und deine Eingabe geht an keinen externen Dienst.';
