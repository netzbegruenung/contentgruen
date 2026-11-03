import { Subject } from 'rxjs';

import {
  VORLAGE_PARAM,
  Vorlage,
  VorlageAusAdresse,
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

  describe('VorlageAusAdresse', () => {
    const vorlage = (id: string): Vorlage => ({ id, titel: `Titel ${id}`, text: '' });

    it('verwirft eine spaete Antwort fuer eine alte Adresse', () => {
      const antworten: Record<string, Subject<Vorlage>> = { a: new Subject(), b: new Subject() };
      const ausAdresse = new VorlageAusAdresse((id) => antworten[id], () => undefined);

      ausAdresse.uebernehmen('a');
      ausAdresse.uebernehmen('b');
      antworten['a'].next(vorlage('a'));
      expect(ausAdresse.vorlage).toBeNull();

      antworten['b'].next(vorlage('b'));
      expect(ausAdresse.vorlage!.id).toBe('b');
    });

    it('ohne ?vorlage= bleibt nichts uebrig, auch keine spaete Antwort', () => {
      const antwort = new Subject<Vorlage>();
      const ausAdresse = new VorlageAusAdresse(() => antwort, () => undefined);

      ausAdresse.uebernehmen('a');
      ausAdresse.uebernehmen(null);
      antwort.next(vorlage('a'));

      expect(ausAdresse.vorlage).toBeNull();
    });

    it('meldet, wenn die Vorlage nicht ladbar ist', () => {
      const antwort = new Subject<Vorlage>();
      const nichtLadbar = jasmine.createSpy('nichtLadbar');
      const ausAdresse = new VorlageAusAdresse(() => antwort, nichtLadbar);

      ausAdresse.uebernehmen('weg');
      antwort.error('404');

      expect(nichtLadbar).toHaveBeenCalledWith('404');
      expect(ausAdresse.vorlage).toBeNull();
    });
  });

  it('nennt im Hinweis das Original', () => {
    expect(vorlageHinweis({ id: 'k-1', titel: 'Waermepumpen', text: '' })).toContain('Variante von „Waermepumpen“');
  });
});
