import { herkunftText } from './herkunft-text';
import { KartenDaten } from './karten-daten';

describe('herkunftText', () => {
  function daten(felder: Partial<KartenDaten> = {}): KartenDaten {
    return {
      id: 'b-1',
      typ: 'commentary',
      titel: 'Wärmepumpe lohnt sich auch im Altbau',
      text: 'Text',
      erstellt: '',
      autor: null,
      autorName: null,
      nutzung: 0,
      quellen: [],
      ...felder,
    };
  }

  it('ist leer ohne Herkunft', () => {
    expect(herkunftText(daten())).toBe('');
  });

  it('nennt eine einzelne Herkunft in einer Zeile, mit Beschreibung vor der Adresse', () => {
    const text = herkunftText(
      daten({ quellen: [{ id: 'r-1', url: 'https://example.org/studie', beschreibung: 'Studie des Umweltbundesamts' }] }),
    );

    expect(text).toBe('Herkunft: Studie des Umweltbundesamts: https://example.org/studie');
  });

  it('listet mehrere Herkuenfte untereinander', () => {
    const text = herkunftText(
      daten({
        typ: 'generictext',
        quellen: [
          { id: 'r-1', url: 'https://example.org/a' },
          { id: 'r-2', beschreibung: 'Rede im Landtag, 12. März' },
        ],
      }),
    );

    expect(text).toBe('Herkunft:\n- https://example.org/a\n- Rede im Landtag, 12. März');
  });

  it('laesst Herkunftsangaben ohne Adresse und ohne Beschreibung weg', () => {
    expect(herkunftText(daten({ quellen: [{ id: '123e4567-e89b-12d3-a456-426614174000' }] }))).toBe('');
  });

  it('schneidet Leerzeichen ab und laesst Angaben aus lauter Leerzeichen weg', () => {
    const text = herkunftText(
      daten({
        quellen: [
          { id: 'r-1', url: ' https://example.org/a ', beschreibung: '   ' },
          { id: 'r-2', url: '  ', beschreibung: ' ' },
        ],
      }),
    );

    expect(text).toBe('Herkunft: https://example.org/a');
  });

  it('nimmt Herkunftsangaben nur bei Kommentar und Hintergrundinfo', () => {
    const quellen = [{ id: 'r-1', url: 'https://example.org/a' }];

    expect(herkunftText(daten({ typ: 'statement', quellen }))).toBe('');
    expect(herkunftText(daten({ typ: 'image', quellen }))).toBe('');
  });

  it('nimmt beim Post den Link als Herkunft', () => {
    const text = herkunftText(daten({ typ: 'post', extra: { postUrl: 'https://social.example/posts/1' } }));

    expect(text).toBe('Herkunft: https://social.example/posts/1');
  });

  it('kennt beim Bild keine Herkunft', () => {
    expect(herkunftText(daten({ typ: 'image', bildUrl: 'https://example.org/bild.jpg' }))).toBe('');
  });
});
