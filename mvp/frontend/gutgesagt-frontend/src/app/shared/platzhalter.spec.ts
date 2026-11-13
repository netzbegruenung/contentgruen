import { ohnePlatzhalter, platzhalterFuellen, platzhalterIn } from './platzhalter';

describe('Platzhalter füllen (Persona-Test Dennis)', () => {
  const TEXT = 'Vögel und Klima. [Hier ein eigenes Erlebnis: Windpark in deiner Gegend] Deshalb ja.';

  it('findet die Platzhalter mit ihrem Hinweis, ohne Klammern', () => {
    expect(platzhalterIn(TEXT)).toEqual([{ hinweis: 'Hier ein eigenes Erlebnis: Windpark in deiner Gegend' }]);
    expect(platzhalterIn('A [Hier x] B [Hier y]')).toEqual([{ hinweis: 'Hier x' }, { hinweis: 'Hier y' }]);
  });

  it('findet in Texten ohne Platzhalter nichts, auch nicht bei anderen Klammern', () => {
    expect(platzhalterIn('Siehe [1] und [sic].')).toEqual([]);
    expect(platzhalterIn('')).toEqual([]);
    expect(platzhalterIn(null)).toEqual([]);
  });

  it('setzt den eigenen Satz an die Stelle der Klammer', () => {
    expect(platzhalterFuellen(TEXT, ['Bei uns stehen drei Windräder, die Störche brüten weiter.'])).toBe(
      'Vögel und Klima. Bei uns stehen drei Windräder, die Störche brüten weiter. Deshalb ja.',
    );
  });

  it('füllt mehrere Platzhalter in ihrer Reihenfolge und nimmt Leerzeichen am Rand weg', () => {
    expect(platzhalterFuellen('A [Hier x] B [Hier y] C', ['  eins ', 'zwei'])).toBe('A eins B zwei C');
  });

  it('lässt den übrigen Text unverändert', () => {
    const text = 'Erste Zeile  mit zwei Leerzeichen.\n\n  Eingerückt. [Hier x]';
    expect(platzhalterFuellen(text, ['Satz.'])).toBe('Erste Zeile  mit zwei Leerzeichen.\n\n  Eingerückt. Satz.');
  });

  it('entfernt ohne Satz die Klammer-Stelle sauber', () => {
    expect(ohnePlatzhalter(TEXT)).toBe('Vögel und Klima. Deshalb ja.');
    expect(ohnePlatzhalter('Gut. [Hier …]. Weiter.')).toBe('Gut. Weiter.');
    expect(ohnePlatzhalter('Das liegt an [Hier deine Stadt].')).toBe('Das liegt an.');
    expect(ohnePlatzhalter('[Hier …] Danach.')).toBe('Danach.');
    expect(ohnePlatzhalter('Davor. [Hier …]')).toBe('Davor.');
  });

  it('nimmt einen Absatz, der nur aus dem Platzhalter bestand, ganz heraus', () => {
    expect(ohnePlatzhalter('Erster Absatz.\n\n[Hier ein eigenes Erlebnis: …]\n\nLetzter Absatz.')).toBe(
      'Erster Absatz.\n\nLetzter Absatz.',
    );
    expect(ohnePlatzhalter('Text. [Hier …]\n\nHerkunft: https://example.org')).toBe('Text.\n\nHerkunft: https://example.org');
  });

  it('behandelt einen leeren Satz wie keinen', () => {
    expect(platzhalterFuellen(TEXT, ['   '])).toBe('Vögel und Klima. Deshalb ja.');
  });

  it('lässt zwischen zwei Kommas oder Semikolons nur eins stehen', () => {
    expect(ohnePlatzhalter('Gut, [Hier ein Erlebnis], weiter.')).toBe('Gut, weiter.');
    expect(ohnePlatzhalter('Gut; [Hier ein Erlebnis]; weiter.')).toBe('Gut; weiter.');
    expect(ohnePlatzhalter('Gut,[Hier x],weiter.')).toBe('Gut,weiter.');
  });

  it('schließt eine Klammer direkt hinter dem Rest und nimmt eine leere Klammer ganz weg', () => {
    expect(ohnePlatzhalter('A (z. B. [Hier x]) b')).toBe('A (z. B.) b');
    expect(ohnePlatzhalter('A ([Hier x]) b')).toBe('A b');
    expect(ohnePlatzhalter('A ( [Hier x] ).')).toBe('A.');
  });

  // Bekanntes Verhalten (vorlagen-luecke.ts, LUECKE): Ein Platzhalter endet an der ersten
  // schließenden Klammer und reicht nicht über einen Zeilenumbruch.
  it('erkennt verschachtelte und mehrzeilige Platzhalter nur so weit wie LUECKE', () => {
    expect(platzhalterIn('A [Hier ein [x] Erlebnis] B')).toEqual([{ hinweis: 'Hier ein [x' }]);
    expect(ohnePlatzhalter('A [Hier ein [x] Erlebnis] B')).toBe('A Erlebnis] B');
    expect(platzhalterIn('A [Hier ein\nErlebnis] B')).toEqual([]);
    expect(ohnePlatzhalter('A [Hier ein\nErlebnis] B')).toBe('A [Hier ein\nErlebnis] B');
  });
});
