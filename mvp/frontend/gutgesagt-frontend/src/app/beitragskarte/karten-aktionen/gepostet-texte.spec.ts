import { GEPOSTET_NICHT_GEZAEHLT, gepostetDank } from './gepostet-texte';

describe('gepostetDank (#643)', () => {
  it('nennt die erste Person der Woche', () => {
    expect(gepostetDank(1)).toBe('Danke! Du bist diese Woche die erste Person, die meldet, dass sie öffentlich kontert.');
  });

  it('nennt die echte Zahl der Woche', () => {
    expect(gepostetDank(7)).toBe('Danke! Diese Woche haben 7 Menschen gemeldet, dass sie öffentlich gekontert haben. Du bist dabei.');
  });

  it('dankt auch, wenn das Zählen scheitert, ohne eine Zahl', () => {
    expect(gepostetDank(null)).toBe(GEPOSTET_NICHT_GEZAEHLT);
  });
});
