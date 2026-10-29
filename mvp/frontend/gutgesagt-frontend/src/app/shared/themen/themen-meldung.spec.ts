import { themenHinweis } from './themen-meldung';

describe('themenHinweis (#455)', () => {
  const KLIMA = { schluessel: 'klima', name: 'Klima' };
  const HEIZEN = { schluessel: 'energie-heizen', name: 'Energie und Heizen' };

  it('sagt nichts ohne gewaehlte Themen', () => {
    expect(themenHinweis([], [KLIMA])).toBeNull();
  });

  it('sagt nichts, wenn die Aussage die gewaehlten bekam', () => {
    expect(themenHinweis(['energie-heizen', 'klima'], [KLIMA, HEIZEN])).toBeNull();
  });

  it('nennt die Themen einer vorhandenen Aussage, die ihre behielt', () => {
    expect(themenHinweis(['energie-heizen'], [KLIMA])).toBe('Diese Aussage gibt es schon. Themen: Klima.');
  });

  it('nennt mehrere Themen in derselben Form', () => {
    expect(themenHinweis(['soziales'], [KLIMA, HEIZEN])).toBe('Diese Aussage gibt es schon. Themen: Klima, Energie und Heizen.');
  });

  it('sagt, wenn das Zuordnen scheiterte', () => {
    expect(themenHinweis(['klima'], [])).toBe('Themen nicht gespeichert.');
  });
});
