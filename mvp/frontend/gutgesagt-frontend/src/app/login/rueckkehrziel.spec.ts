import {
  RUECKKEHRZIEL_SCHLUESSEL,
  rueckkehrzielLesen,
  rueckkehrzielLoeschen,
  rueckkehrzielMerken,
} from './rueckkehrziel';

describe('Rueckkehrziel nach dem Anmelden', () => {
  beforeEach(() => sessionStorage.removeItem(RUECKKEHRZIEL_SCHLUESSEL));
  afterEach(() => sessionStorage.removeItem(RUECKKEHRZIEL_SCHLUESSEL));

  it('merkt sich ein echtes Ziel und liest es wieder', () => {
    rueckkehrzielMerken('/contribute');

    expect(sessionStorage.getItem(RUECKKEHRZIEL_SCHLUESSEL)).toBe('/contribute');
    expect(rueckkehrzielLesen()).toBe('/contribute');
  });

  it('legt ohne Rueckkehrziel nichts ab: weder die Startseite noch eine Login-Seite', () => {
    for (const ziel of ['/', '', '/login', '/login/managed?returnUrl=%2F']) {
      rueckkehrzielMerken(ziel);
      expect(sessionStorage.getItem(RUECKKEHRZIEL_SCHLUESSEL)).withContext(ziel).toBeNull();
    }
  });

  it('verwirft ein altes Ziel, wenn das neue keines ist', () => {
    rueckkehrzielMerken('/contribute');

    rueckkehrzielMerken('/');

    expect(sessionStorage.getItem(RUECKKEHRZIEL_SCHLUESSEL)).toBeNull();
  });

  it('liest ein abgelegtes "/" oder eine Login-Seite als kein Ziel', () => {
    sessionStorage.setItem(RUECKKEHRZIEL_SCHLUESSEL, '/');
    expect(rueckkehrzielLesen()).toBeNull();

    sessionStorage.setItem(RUECKKEHRZIEL_SCHLUESSEL, '/login/managed');
    expect(rueckkehrzielLesen()).toBeNull();
  });

  it('loescht das Ziel', () => {
    rueckkehrzielMerken('/contribute');

    rueckkehrzielLoeschen();

    expect(sessionStorage.getItem(RUECKKEHRZIEL_SCHLUESSEL)).toBeNull();
  });

  it('wirft nicht, wenn der Browser den sessionStorage sperrt', () => {
    const spione = [
      spyOn(Storage.prototype, 'getItem').and.throwError('SecurityError'),
      spyOn(Storage.prototype, 'setItem').and.throwError('SecurityError'),
      spyOn(Storage.prototype, 'removeItem').and.throwError('SecurityError'),
    ];

    expect(rueckkehrzielLesen()).toBeNull();
    expect(() => rueckkehrzielMerken('/contribute')).not.toThrow();
    expect(() => rueckkehrzielMerken('/')).not.toThrow();
    expect(() => rueckkehrzielLoeschen()).not.toThrow();
    // Der afterEach raeumt mit removeItem auf; der Spy wuerde dort sonst werfen.
    spione.forEach((spion) => spion.and.callThrough());
  });
});
