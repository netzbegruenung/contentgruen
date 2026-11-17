import { STANDARD_ZIEL, VORSCHAU_SCHRITTE, vorschauZiel } from './vorschau-schritte';

describe('Vorschau mit Konto: Schritte und Ziel', () => {
  it('hat drei Schritte mit Begriffen aus dem Glossar, je Bild, Satz und Alternativtext', () => {
    expect(VORSCHAU_SCHRITTE.map((s) => s.titel)).toEqual(['Einwerfen', 'Ausformulieren', 'Bewerten']);
    for (const s of VORSCHAU_SCHRITTE) {
      expect(s.bild).toMatch(/^vorschau\/[a-z]+-v\d+\.webp$/);
      expect(s.satz.length).toBeGreaterThan(10);
      expect(s.alt.length).toBeGreaterThan(20);
    }
  });

  it('nimmt Pfade dieser App als Ziel, samt Query', () => {
    expect(vorschauZiel('/einwerfen')).toBe('/einwerfen');
    expect(vorschauZiel('/contribute?x=1')).toBe('/contribute?x=1');
  });

  it('weicht bei fehlenden, fremden oder kreisenden Zielen auf Beitragen aus', () => {
    for (const wert of [null, undefined, '', 'einwerfen', '//fremd.example', '/\\fremd.example', 'https://fremd.example', '/login?returnUrl=%2F', '/mit-konto?ziel=%2F']) {
      expect(vorschauZiel(wert)).withContext(String(wert)).toBe(STANDARD_ZIEL);
    }
  });
});
