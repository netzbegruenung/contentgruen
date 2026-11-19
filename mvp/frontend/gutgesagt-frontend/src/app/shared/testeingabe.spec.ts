import { TESTEINGABEN, TESTEINGABE_BEISPIEL, TesteingabeArt, normalisieren, testeingabeArt, testeingabeText } from './testeingabe';

describe('Testeingabe', () => {
  describe('testeingabeArt', () => {
    it('erkennt jedes Wort der Liste in seiner Gruppe', () => {
      for (const art of Object.keys(TESTEINGABEN) as TesteingabeArt[]) {
        for (const wort of TESTEINGABEN[art].woerter) {
          expect(testeingabeArt(wort)).withContext(wort).toBe(art);
        }
      }
    });

    it('ignoriert Gross- und Kleinschreibung und Leerraum aussen', () => {
      expect(testeingabeArt('TEST')).toBe('test');
      expect(testeingabeArt('  Hallo ')).toBe('gruss');
      expect(testeingabeArt('Was Ist Das')).toBe('frage');
      expect(testeingabeArt('was   ist  das')).toBe('frage');
    });

    it('ignoriert Satzzeichen am Ende', () => {
      expect(testeingabeArt('Hallo!')).toBe('gruss');
      expect(testeingabeArt('test.')).toBe('test');
      expect(testeingabeArt('Was ist das?')).toBe('frage');
      expect(testeingabeArt('Hilfe!!! ')).toBe('frage');
      expect(testeingabeArt('moin…')).toBe('gruss');
    });

    it('zaehlt keine Teilwoerter und keine laengeren Eingaben', () => {
      for (const eingabe of [
        'Testergebnis Corona',
        'Testergebnis',
        'Hallo, die Grünen wollen uns das Auto wegnehmen',
        'hi there',
        'Hilfe für Heizungstausch',
        '1234',
        'test test',
        '',
        '   ',
        '?',
        'Windräder töten die Vögel!',
      ]) {
        expect(testeingabeArt(eingabe)).withContext(eingabe).toBeNull();
      }
    });

    it('zaehlt Satzzeichen am Anfang oder in der Mitte nicht weg', () => {
      expect(testeingabeArt('!hallo')).toBeNull();
      expect(testeingabeArt('te-st')).toBeNull();
    });
  });

  describe('normalisieren', () => {
    it('macht klein, kuerzt Leerraum und Satzzeichen am Ende', () => {
      expect(normalisieren('  Wie geht  DAS ?! ')).toBe('wie geht das');
    });
  });

  describe('testeingabeText', () => {
    it('waehlt per Zufall einen Text der Gruppe, auch an den Raendern', () => {
      const texte = TESTEINGABEN.test.texte;
      expect(testeingabeText('test', () => 0)).toBe(texte[0]);
      expect(testeingabeText('test', () => 0.5)).toBe(texte[1]);
      expect(testeingabeText('test', () => 0.9999)).toBe(texte[texte.length - 1]);
      expect(testeingabeText('test', () => 1)).toBe(texte[texte.length - 1]);
    });
  });

  describe('Liste und Texte', () => {
    const alle = (Object.keys(TESTEINGABEN) as TesteingabeArt[]).map((art) => TESTEINGABEN[art]);

    it('das Beispiel ist selbst keine Testeingabe, ein Klick sucht es also', () => {
      expect(TESTEINGABE_BEISPIEL.length).toBeGreaterThan(10);
      expect(testeingabeArt(TESTEINGABE_BEISPIEL)).toBeNull();
    });

    it('jede Gruppe hat zwei oder drei Texte', () => {
      for (const gruppe of alle) {
        expect(gruppe.texte.length).toBeGreaterThanOrEqual(2);
        expect(gruppe.texte.length).toBeLessThanOrEqual(3);
      }
    });

    it('Texte sind hoechstens 140 Zeichen lang und ohne Gedankenstriche', () => {
      for (const text of alle.flatMap((g) => g.texte)) {
        expect([...text].length).withContext(text).toBeLessThanOrEqual(140);
        expect(text).withContext(text).not.toMatch(/[–—]| - /);
      }
    });

    it('jedes Wort steht so da, wie normalisieren es liefert, und nur in einer Gruppe', () => {
      const woerter = alle.flatMap((g) => g.woerter);
      for (const wort of woerter) {
        expect(normalisieren(wort)).toBe(wort);
      }
      expect(new Set(woerter).size).toBe(woerter.length);
    });
  });
});
