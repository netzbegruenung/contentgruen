import { hatLuecke, textStuecke } from './vorlagen-luecke';

describe('Vorlagen-Luecke (#640, R38)', () => {
  it('erkennt den Platzhalter der Schreibregel', () => {
    expect(hatLuecke('Gut. [Hier ein eigenes Erlebnis: …]')).toBeTrue();
    expect(hatLuecke('[Hier deine Stadt]')).toBeTrue();
  });

  it('haelt andere eckige Klammern nicht fuer eine Luecke', () => {
    expect(hatLuecke('Siehe [1] und [sic].')).toBeFalse();
    expect(hatLuecke('[Hierarchie]')).toBeFalse();
    expect(hatLuecke('')).toBeFalse();
    expect(hatLuecke(null)).toBeFalse();
  });

  it('zerlegt den Text in Stuecke, die Luecken als eigene', () => {
    expect(textStuecke('A [Hier x] B [Hier y]')).toEqual([
      { text: 'A ', luecke: false },
      { text: '[Hier x]', luecke: true },
      { text: ' B ', luecke: false },
      { text: '[Hier y]', luecke: true },
    ]);
  });

  it('gibt ohne Luecke den ganzen Text als ein Stueck', () => {
    expect(textStuecke('Ohne')).toEqual([{ text: 'Ohne', luecke: false }]);
    expect(textStuecke('')).toEqual([{ text: '', luecke: false }]);
  });
});
