import { KartenDaten } from './karten-daten';

/** Nur Kommentar und Hintergrundinfo tragen Herkunftsangaben; Karte und Kopieren fragen beide hier. */
export function tragtHerkunftsangaben(typ: string | null): boolean {
  return typ === 'commentary' || typ === 'generictext';
}

/**
 * Die Herkunft eines Beitrags als Text zum Anhaengen beim Kopieren ("Text + Herkunft").
 *
 * Gemeint ist die eigentliche Herkunft, nie ein Link auf Gut gesagt. Kommentar und
 * Hintergrundinfo bringen ihre Herkunftsangaben mit, beim Post ersetzt der Link die
 * Herkunft (GLOSSARY.md). Leer, wenn es keine gibt; dann bietet die Karte keine Wahl an.
 */
export function herkunftText(daten: KartenDaten): string {
  const zeilen = herkunftZeilen(daten);

  if (zeilen.length === 0) {
    return '';
  }
  if (zeilen.length === 1) {
    return `Herkunft: ${zeilen[0]}`;
  }
  return ['Herkunft:', ...zeilen.map((zeile) => `- ${zeile}`)].join('\n');
}

function herkunftZeilen(daten: KartenDaten): string[] {
  if (daten.typ === 'post') {
    return nichtLeer([daten.extra?.postUrl]);
  }
  if (!tragtHerkunftsangaben(daten.typ)) {
    return [];
  }
  return nichtLeer(daten.quellen.map((angabe) => nichtLeer([angabe.beschreibung, angabe.url]).join(': ')));
}

function nichtLeer(werte: (string | undefined)[]): string[] {
  return werte.map((wert) => wert?.trim() ?? '').filter(Boolean);
}
