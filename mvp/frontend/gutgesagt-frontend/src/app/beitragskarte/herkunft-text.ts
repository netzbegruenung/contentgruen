import { KartenDaten } from './karten-daten';

/**
 * Die Herkunft eines Beitrags als Text zum Anhaengen beim Kopieren ("Text + Herkunft").
 *
 * Gemeint ist die eigentliche Herkunft, nie ein Link auf Gut gesagt. Kommentar und
 * Hintergrundinfo bringen ihre Herkunftsangaben mit, beim Post ersetzt der Link die
 * Herkunft (GLOSSARY.md). Leer, wenn es keine gibt; dann bietet die Karte keine Wahl an.
 */
export function herkunftText(daten: KartenDaten): string {
  const zeilen =
    daten.typ === 'post'
      ? [daten.extra?.postUrl].filter((url): url is string => !!url)
      : daten.quellen
          .map((quelle) => [quelle.beschreibung, quelle.url].filter(Boolean).join(': '))
          .filter(Boolean);

  if (zeilen.length === 0) {
    return '';
  }
  if (zeilen.length === 1) {
    return `Herkunft: ${zeilen[0]}`;
  }
  return ['Herkunft:', ...zeilen.map((zeile) => `- ${zeile}`)].join('\n');
}
