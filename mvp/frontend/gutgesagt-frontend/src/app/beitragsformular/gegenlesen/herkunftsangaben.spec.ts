import { hatFundstelle, herkunftOhneFundstelle } from './herkunftsangaben';

describe('Herkunft ohne Fundstelle', () => {
  for (const angabe of [
    'https://www.umweltbundesamt.de',
    'https://www.umweltbundesamt.de/',
    'http://example.org/index.html',
    'https://example.org/de/',
    'www.destatis.de',
    'destatis.de',
    '/mnt/data/Argumentationshilfe.pdf',
    'file:///C:/Users/x/studie.pdf',
    'C:\\Daten\\studie.pdf',
  ]) {
    it(`„${angabe}“ ist keine Fundstelle`, () => {
      expect(hatFundstelle(angabe)).toBeFalse();
    });
  }

  for (const angabe of [
    'https://www.umweltbundesamt.de/themen/verkehr/emissionen',
    'https://example.org/?id=4711',
    'www.destatis.de/DE/Themen/Wirtschaft/_inhalt.html',
    'Umweltbundesamt, Bericht Verkehr 2024',
  ]) {
    it(`„${angabe}“ ist eine Fundstelle`, () => {
      expect(hatFundstelle(angabe)).toBeTrue();
    });
  }

  it('meldet nur, wenn keine Angabe eine Fundstelle nennt', () => {
    expect(herkunftOhneFundstelle([{ reference_string: 'https://www.bmwk.de' }])).toBeTrue();
    expect(
      herkunftOhneFundstelle([{ reference_string: 'https://www.bmwk.de' }, { reference_string: 'https://www.bmwk.de/a' }]),
    ).toBeFalse();
  });

  it('zählt Links im Text mit, ohne Satzzeichen am Ende', () => {
    expect(herkunftOhneFundstelle([{ reference_string: 'https://www.bmwk.de' }], 'Mehr auf www.bmwk.de/bericht.')).toBeFalse();
    expect(herkunftOhneFundstelle([], 'Siehe www.bmwk.de.')).toBeTrue();
  });

  it('ohne Herkunft ist es keine Frage der Fundstelle', () => {
    expect(herkunftOhneFundstelle(undefined, null)).toBeFalse();
    expect(herkunftOhneFundstelle([{ reference_string: '  ' }, null])).toBeFalse();
  });
});
