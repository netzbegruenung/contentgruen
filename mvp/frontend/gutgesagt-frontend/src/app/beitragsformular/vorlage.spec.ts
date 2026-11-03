import {
  VORLAGE_PARAM,
  kannVorlageSein,
  vorlageAdresse,
  vorlageAusHintergrundinfo,
  vorlageAusKommentar,
  vorlageHinweis,
} from './vorlage';

describe('vorlage (#356)', () => {
  it('gibt es nur fuer Kommentar und Hintergrundinfo', () => {
    expect(kannVorlageSein('commentary')).toBeTrue();
    expect(kannVorlageSein('generictext')).toBeTrue();
    expect(kannVorlageSein('post')).toBeFalse();
    expect(kannVorlageSein('image')).toBeFalse();
    expect(kannVorlageSein(null)).toBeFalse();
  });

  it('fuehrt ins Formular des Typs mit der ID in der Adresse', () => {
    expect(vorlageAdresse('generictext', 'g-1')).toEqual({
      pfad: '/workflow/add-generictext',
      queryParams: { [VORLAGE_PARAM]: 'g-1' },
    });
  });

  it('uebernimmt vom Kommentar Text, Fassungen, Zweck und Stil, leere Fassungen nicht', () => {
    const vorlage = vorlageAusKommentar({
      id: 'k-1',
      title: 'Titel',
      text: 'Text',
      short_text: '',
      long_text: 'Lang',
      zweck: 'eigene_leute',
      style: 'bissig',
    } as any);

    expect(vorlage).toEqual({
      id: 'k-1',
      titel: 'Titel',
      text: 'Text',
      kurz: undefined,
      lang: 'Lang',
      zweck: 'eigene_leute',
      stil: 'bissig',
    });
  });

  it('uebernimmt von der Hintergrundinfo Titel und Text', () => {
    expect(vorlageAusHintergrundinfo({ id: 'g-1', title: 'T', text: 'X', references: [] } as any)).toEqual({
      id: 'g-1',
      titel: 'T',
      text: 'X',
    });
  });

  it('nennt im Hinweis das Original', () => {
    expect(vorlageHinweis({ id: 'k-1', titel: 'Waermepumpen', text: '' })).toContain('Variante von „Waermepumpen“');
  });
});
