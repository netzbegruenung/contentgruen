import { DublettenTexte, Vorhanden, dublettenHinweis, dublettenKurzhinweis, offeneEntscheidung, vorhandenAus } from './dublette';

const TEXTE: DublettenTexte = {
  eigenHinweis: 'Hast du schon gespeichert.',
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

  describe('offeneEntscheidung', () => {
    it('offen nur mit vorhandenem und ohne Wahl', () => {
      expect(offeneEntscheidung(null)).toBeFalse();
      expect(offeneEntscheidung(vorhanden())).toBeTrue();
      expect(offeneEntscheidung(vorhanden({ gewaehlt: 'zugestimmt' }))).toBeFalse();
    });
  });

  describe('dublettenHinweis', () => {
    it('vor der Wahl: fremd nennt jemand anderen, mit Aussage auch den anderen Weg; eigen sagt es', () => {
      expect(dublettenHinweis(vorhanden(), TEXTE, true)).toBe(`${TEXTE.fremdHinweis} ${TEXTE.fremdZuordnen}`);
      expect(dublettenHinweis(vorhanden(), TEXTE, false)).toBe(TEXTE.fremdHinweis);
      expect(dublettenHinweis(vorhanden({ eigen: true }), TEXTE, true)).toBe(TEXTE.eigenHinweis);
      expect(dublettenHinweis(vorhanden({ eigen: true }), TEXTE, false)).toBe(TEXTE.eigenHinweis);
    });

    it('nach der Wahl: zugestimmt, genommen oder verknuepft', () => {
      expect(dublettenHinweis(vorhanden({ gewaehlt: 'zugestimmt' }), TEXTE, true)).toBe(TEXTE.zugestimmt);
      expect(dublettenHinweis(vorhanden({ eigen: true, gewaehlt: 'genommen' }), TEXTE, false)).toBe(TEXTE.genommen);
      expect(dublettenHinweis(vorhanden({ eigen: true, gewaehlt: 'genommen', aussage: 'A' }), TEXTE, true)).toBe(
        'Verknüpft mit A.',
      );
    });
  });

  describe('dublettenKurzhinweis', () => {
    it('ein Satz: eigen oder von jemand anderem, ohne den Weg ueber die Karte', () => {
      expect(dublettenKurzhinweis(vorhanden({ eigen: true }), TEXTE)).toBe(TEXTE.eigenHinweis);
      expect(dublettenKurzhinweis(vorhanden(), TEXTE)).toBe(TEXTE.fremdHinweis);
    });
  });
});
