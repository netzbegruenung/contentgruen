import { KartenDaten } from '../beitragskarte/karten-daten';
import { nachNutzung, wirkungssatz } from './wirkung';

describe('wirkungssatz', () => {
  it('nennt Nutzung und Woche', () => {
    expect(wirkungssatz(4, 3, 2)).toBe('Deine 4 Beiträge wurden 3-mal genutzt, 2 davon diese Woche.');
  });

  it('sagt "alle diese Woche", wenn alles aus dieser Woche ist', () => {
    expect(wirkungssatz(4, 3, 3)).toBe('Deine 4 Beiträge wurden 3-mal genutzt, alle diese Woche.');
    expect(wirkungssatz(1, 1, 1)).toBe('Dein Beitrag wurde einmal genutzt, diese Woche.');
  });

  it('laesst die Woche ohne Zahl oder bei 0 weg', () => {
    expect(wirkungssatz(2, 5, null)).toBe('Deine 2 Beiträge wurden 5-mal genutzt.');
    expect(wirkungssatz(2, 5, 0)).toBe('Deine 2 Beiträge wurden 5-mal genutzt.');
  });

  it('sagt ohne Nutzung "noch nicht genutzt"', () => {
    expect(wirkungssatz(1, 0, 0)).toBe('Dein Beitrag wurde noch nicht genutzt.');
  });
});

describe('nachNutzung', () => {
  const karte = (id: string, nutzung: number | null) => ({ id, nutzung }) as KartenDaten;

  it('stellt die meistgenutzten nach vorn und haelt sonst die Reihenfolge', () => {
    const sortiert = nachNutzung([karte('a', 0), karte('b', 4), karte('c', null), karte('d', 4), karte('e', 1)]);

    expect(sortiert.map((k) => k.id)).toEqual(['b', 'd', 'e', 'a', 'c']);
  });
});
