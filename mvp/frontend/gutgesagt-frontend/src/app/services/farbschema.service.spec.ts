import { TestBed } from '@angular/core/testing';

import { FARBSCHEMA_SCHLUESSEL, FarbschemaService } from './farbschema.service';

describe('FarbschemaService', () => {
  let systemDunkel: boolean;
  let systemWechsel: ((ereignis: { matches: boolean }) => void) | null;
  let vorher: string | null;

  function dienst(): FarbschemaService {
    return TestBed.inject(FarbschemaService);
  }

  function attribut(): string | null {
    return document.documentElement.getAttribute('data-theme');
  }

  beforeEach(() => {
    vorher = attribut();
    systemDunkel = false;
    systemWechsel = null;
    localStorage.removeItem(FARBSCHEMA_SCHLUESSEL);
    spyOn(window, 'matchMedia').and.callFake(
      () =>
        ({
          matches: systemDunkel,
          addEventListener: (_: string, rueckruf: (ereignis: { matches: boolean }) => void) => (systemWechsel = rueckruf),
        }) as unknown as MediaQueryList,
    );
    TestBed.configureTestingModule({});
  });

  // Das Attribut gilt fuer das ganze Testdokument: zuruecksetzen, damit andere Specs hell bleiben
  afterEach(() => {
    localStorage.removeItem(FARBSCHEMA_SCHLUESSEL);
    if (vorher === null) document.documentElement.removeAttribute('data-theme');
    else document.documentElement.setAttribute('data-theme', vorher);
  });

  it('folgt ohne eigene Wahl dem Geraet', () => {
    systemDunkel = true;
    expect(dienst().dunkel()).toBeTrue();
    expect(attribut()).toBe('dark');
  });

  it('nimmt die gemerkte Wahl vor dem Geraet', () => {
    systemDunkel = true;
    localStorage.setItem(FARBSCHEMA_SCHLUESSEL, 'light');
    expect(dienst().dunkel()).toBeFalse();
    expect(attribut()).toBe('light');
  });

  it('schaltet um, setzt das Attribut und merkt sich die Wahl', () => {
    dienst().umschalten();
    expect(dienst().schema()).toBe('dark');
    expect(attribut()).toBe('dark');
    expect(localStorage.getItem(FARBSCHEMA_SCHLUESSEL)).toBe('dark');

    dienst().umschalten();
    expect(attribut()).toBe('light');
    expect(localStorage.getItem(FARBSCHEMA_SCHLUESSEL)).toBe('light');
  });

  it('folgt einem Wechsel am Geraet nur ohne eigene Wahl', () => {
    const farbschema = dienst();
    systemWechsel!({ matches: true });
    expect(farbschema.dunkel()).toBeTrue();

    farbschema.umschalten();
    systemWechsel!({ matches: true });
    expect(farbschema.dunkel()).toBeFalse();
  });

  it('schaltet ohne Speicher trotzdem um', () => {
    spyOn(Storage.prototype, 'getItem').and.throwError('gesperrt');
    spyOn(Storage.prototype, 'setItem').and.throwError('gesperrt');
    systemDunkel = true;
    const farbschema = dienst();
    expect(farbschema.dunkel()).toBeTrue();

    farbschema.umschalten();
    expect(farbschema.dunkel()).toBeFalse();
    expect(attribut()).toBe('light');
  });
});
