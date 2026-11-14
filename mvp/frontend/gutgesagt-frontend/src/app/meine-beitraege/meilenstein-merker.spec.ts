import { MEILENSTEINE_GESEHEN_SCHLUESSEL, gesehenLesen, gesehenMerken, merkerEntfernen } from './meilenstein-merker';
import { Meilenstein } from '../services/usage-tracking.service';

describe('Meilenstein-Merker (#351)', () => {
  const erreicht = { kennung: 'einwurf-1', erreicht: true } as Meilenstein;
  const offen = { kennung: 'nutzung-1', erreicht: false } as Meilenstein;

  afterEach(() => localStorage.removeItem(MEILENSTEINE_GESEHEN_SCHLUESSEL));

  it('nutzt einen festen Schlüssel ohne Angaben über die Person', () => {
    gesehenMerken('kim-1', [erreicht]);

    expect(MEILENSTEINE_GESEHEN_SCHLUESSEL).toBe('gutgesagt-meilensteine-gesehen');
    expect(localStorage.getItem(MEILENSTEINE_GESEHEN_SCHLUESSEL)).toBe('["einwurf-1"]');
    expect(localStorage.getItem(MEILENSTEINE_GESEHEN_SCHLUESSEL)).not.toContain('kim');
  });

  it('schreibt nichts ohne Meilensteine und nichts, wenn nichts Erreichtes neu ist', () => {
    gesehenMerken('kim-1', []);
    expect(localStorage.getItem(MEILENSTEINE_GESEHEN_SCHLUESSEL)).toBeNull();

    gesehenMerken('kim-1', [offen]);
    expect(localStorage.getItem(MEILENSTEINE_GESEHEN_SCHLUESSEL)).toBe('[]'); // einmal angelegt
    const setzen = spyOn(Storage.prototype, 'setItem').and.callThrough();
    gesehenMerken('kim-1', [offen]);
    expect(setzen).not.toHaveBeenCalled();
  });

  it('merkt nur erreichte und entfernt sie wieder', () => {
    gesehenMerken('kim-1', [erreicht, offen]);

    expect([...gesehenLesen('kim-1')!]).toEqual(['einwurf-1']);
    merkerEntfernen();
    expect(localStorage.getItem(MEILENSTEINE_GESEHEN_SCHLUESSEL)).toBeNull();
  });

  it('ohne Anmeldung gibt es keinen Merker', () => {
    expect(gesehenLesen(null)).toBeNull();
    gesehenMerken(null, [erreicht]);
    expect(localStorage.getItem(MEILENSTEINE_GESEHEN_SCHLUESSEL)).toBeNull();
  });

  it('übersteht einen kaputten Eintrag', () => {
    localStorage.setItem(MEILENSTEINE_GESEHEN_SCHLUESSEL, '{kaputt');

    expect(gesehenLesen('kim-1')).toBeNull();
  });
});
