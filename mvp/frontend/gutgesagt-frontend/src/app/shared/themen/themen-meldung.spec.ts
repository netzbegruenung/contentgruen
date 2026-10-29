import { themenHinweis } from './themen-meldung';

describe('themenHinweis (#455)', () => {
  const KLIMA = { schluessel: 'klima', name: 'Klima' };
  const HEIZEN = { schluessel: 'energie-heizen', name: 'Energie und Heizen' };
  const AUSSAGE = 'Wärmepumpen sind zu teuer';

  it('sagt nichts ohne gewaehlte Themen', () => {
    expect(themenHinweis([], AUSSAGE, [KLIMA])).toBeNull();
  });

  it('sagt nichts, wenn die Aussage die gewaehlten bekam', () => {
    expect(themenHinweis(['energie-heizen', 'klima'], AUSSAGE, [KLIMA, HEIZEN])).toBeNull();
  });

  it('nennt die Themen einer vorhandenen Aussage, die ihre behielt', () => {
    expect(themenHinweis(['energie-heizen'], AUSSAGE, [KLIMA])).toBe(
      'Diese Aussage gibt es schon: „Wärmepumpen sind zu teuer“ Ihre Themen: Klima.',
    );
  });

  it('sagt, wenn das Zuordnen scheiterte', () => {
    expect(themenHinweis(['klima'], AUSSAGE, [])).toBe('Die Themen konnten nicht gespeichert werden.');
  });
});
