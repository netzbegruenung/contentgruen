import { MEILENSTEINE_GESEHEN_PRAEFIX, gesehenLesen, gesehenMerken, merkerEntfernen, merkerSchluessel } from './meilenstein-merker';
import { Meilenstein } from '../services/usage-tracking.service';

describe('Meilenstein-Merker (#351)', () => {
  const erreicht = { kennung: 'einwurf-1', erreicht: true } as Meilenstein;
  const offen = { kennung: 'nutzung-1', erreicht: false } as Meilenstein;

  afterEach(() => ['kim-1', 'bo-2'].forEach((k) => localStorage.removeItem(merkerSchluessel(k))));

  it('trägt im Schlüssel einen Prüfwert, nicht die Kennung', () => {
    const schluessel = merkerSchluessel('kim-1');

    expect(schluessel.startsWith(MEILENSTEINE_GESEHEN_PRAEFIX)).toBeTrue();
    expect(schluessel).not.toContain('kim-1');
    expect(schluessel).toBe(merkerSchluessel('kim-1'));
    expect(schluessel).not.toBe(merkerSchluessel('bo-2'));
  });

  it('merkt nur erreichte, je Konto getrennt, und entfernt sie wieder', () => {
    gesehenMerken('kim-1', [erreicht, offen]);

    expect([...gesehenLesen('kim-1')!]).toEqual(['einwurf-1']);
    expect([...gesehenLesen('bo-2')!]).toEqual([]);
    merkerEntfernen('kim-1');
    expect(localStorage.getItem(merkerSchluessel('kim-1'))).toBeNull();
  });

  it('ohne Konto gibt es keinen Merker', () => {
    expect(gesehenLesen(null)).toBeNull();
    gesehenMerken(null, [erreicht]);
    merkerEntfernen(null);
  });

  it('übersteht einen kaputten Eintrag', () => {
    localStorage.setItem(merkerSchluessel('kim-1'), '{kaputt');

    expect(gesehenLesen('kim-1')).toBeNull();
  });
});
