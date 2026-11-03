import { DublettenTexte, Vorhanden, dublettenHinweis, vorhandenAus } from './dublette';

const TEXTE: DublettenTexte = {
  hinweis: 'Gibt es schon.',
  fremdHinweis: 'Gibt es schon von jemand anderem.',
  fremdZuordnen: 'Später über die Karte zuordnen.',
  zugestimmt: 'Zugestimmt.',
  genommen: 'Genommen.',
  verknuepft: (aussage) => `Verknüpft mit ${aussage}.`,
};

function vorhanden(teil: Partial<Vorhanden<unknown>> = {}): Vorhanden<unknown> {
  return { id: 'v', titel: null, eigen: false, aussage: null, anfrage: {}, gewaehlt: null, ...teil };
}

describe('Dublette', () => {
  describe('vorhandenAus', () => {
    it('ohne vorhanden in der Antwort: keine Dublette', () => {
      expect(vorhandenAus({}, { id: 'neu', vorhanden: null })).toBeNull();
      expect(vorhandenAus({}, { id: 'neu' })).toBeNull();
    });

    it('merkt die Anfrage ohne die Entscheidung, die sie gebracht hat', () => {
      const ergebnis = vorhandenAus(
        { text: 'x', trotz_dublette_von: 'a', vorhanden_nehmen: 'b' },
        { id: 'v', vorhanden: { titel: 'T', eigen: true } },
      );
      expect(ergebnis).toEqual({ id: 'v', titel: 'T', eigen: true, aussage: null, anfrage: { text: 'x' }, gewaehlt: null });
    });

    it('ohne Titel und eigen: null und false', () => {
      const ergebnis = vorhandenAus({}, { id: 'v', vorhanden: {} })!;
      expect(ergebnis.titel).toBeNull();
      expect(ergebnis.eigen).toBeFalse();
    });
  });

  describe('dublettenHinweis', () => {
    it('vor der Wahl: fremd mit Aussage nennt den anderen Weg, sonst der kurze Hinweis', () => {
      expect(dublettenHinweis(vorhanden(), TEXTE, true)).toBe(`${TEXTE.fremdHinweis} ${TEXTE.fremdZuordnen}`);
      expect(dublettenHinweis(vorhanden(), TEXTE, false)).toBe(TEXTE.hinweis);
      expect(dublettenHinweis(vorhanden({ eigen: true }), TEXTE, true)).toBe(TEXTE.hinweis);
    });

    it('nach der Wahl: zugestimmt, genommen oder verknuepft', () => {
      expect(dublettenHinweis(vorhanden({ gewaehlt: 'zugestimmt' }), TEXTE, true)).toBe(TEXTE.zugestimmt);
      expect(dublettenHinweis(vorhanden({ eigen: true, gewaehlt: 'genommen' }), TEXTE, false)).toBe(TEXTE.genommen);
      expect(dublettenHinweis(vorhanden({ eigen: true, gewaehlt: 'genommen', aussage: 'A' }), TEXTE, true)).toBe(
        'Verknüpft mit A.',
      );
    });
  });
});
