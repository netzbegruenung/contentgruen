import { TestBed } from '@angular/core/testing';

import { FARBSCHEMA_SCHLUESSEL, FarbschemaService, LEISTENFARBE } from './farbschema.service';

describe('FarbschemaService', () => {
  let systemDunkel: boolean;
  let systemWechsel: (() => void) | null;
  let vorher: string | null;
  let leiste: HTMLMetaElement;

  function dienst(): FarbschemaService {
    return TestBed.inject(FarbschemaService);
  }

  function attribut(): string | null {
    return document.documentElement.getAttribute('data-theme');
  }

  /** Das Geraet wechselt seine Einstellung. */
  function geraet(dunkel: boolean): void {
    systemDunkel = dunkel;
    systemWechsel!();
  }

  /** Ein anderer Tab schreibt den Schluessel (dort setItem/removeItem, hier das Ereignis). */
  function andererTab(wert: string | null): void {
    if (wert === null) localStorage.removeItem(FARBSCHEMA_SCHLUESSEL);
    else localStorage.setItem(FARBSCHEMA_SCHLUESSEL, wert);
    window.dispatchEvent(new StorageEvent('storage', { key: FARBSCHEMA_SCHLUESSEL, newValue: wert }));
  }

  beforeEach(() => {
    vorher = attribut();
    systemDunkel = false;
    systemWechsel = null;
    localStorage.removeItem(FARBSCHEMA_SCHLUESSEL);
    leiste = document.createElement('meta');
    leiste.name = 'theme-color';
    document.head.appendChild(leiste);
    spyOn(window, 'matchMedia').and.callFake(
      () =>
        ({
          get matches() {
            return systemDunkel;
          },
          addEventListener: (_: string, rueckruf: () => void) => (systemWechsel = rueckruf),
          removeEventListener: () => undefined,
        }) as unknown as MediaQueryList,
    );
    TestBed.configureTestingModule({});
  });

  // Das Attribut gilt fuer das ganze Testdokument: zuruecksetzen, damit andere Specs hell bleiben
  afterEach(() => {
    TestBed.resetTestingModule();
    leiste.remove();
    localStorage.removeItem(FARBSCHEMA_SCHLUESSEL);
    if (vorher === null) document.documentElement.removeAttribute('data-theme');
    else document.documentElement.setAttribute('data-theme', vorher);
  });

  it('folgt ohne eigene Wahl dem Geraet und faerbt die Browserleiste', () => {
    systemDunkel = true;
    expect(dienst().dunkel()).toBeTrue();
    expect(attribut()).toBe('dark');
    expect(leiste.content).toBe(LEISTENFARBE.dark);
  });

  it('nimmt die gemerkte Wahl vor dem Geraet', () => {
    systemDunkel = true;
    localStorage.setItem(FARBSCHEMA_SCHLUESSEL, 'light');
    expect(dienst().dunkel()).toBeFalse();
    expect(attribut()).toBe('light');
    expect(leiste.content).toBe(LEISTENFARBE.light);
  });

  it('merkt sich nur eine Wahl, die vom Geraet abweicht', () => {
    dienst().umschalten();
    expect(dienst().schema()).toBe('dark');
    expect(attribut()).toBe('dark');
    expect(localStorage.getItem(FARBSCHEMA_SCHLUESSEL)).toBe('dark');

    // Zurueck auf das, was das Geraet ohnehin will: nichts gemerkt
    dienst().umschalten();
    expect(attribut()).toBe('light');
    expect(localStorage.getItem(FARBSCHEMA_SCHLUESSEL)).toBeNull();
  });

  it('folgt dem Geraet wieder, nachdem die Wahl zum Geraet zurueckgeschaltet wurde', () => {
    const farbschema = dienst();
    farbschema.umschalten(); // dunkel, gemerkt
    geraet(true);
    expect(farbschema.dunkel()).toBeTrue();

    farbschema.umschalten(); // hell, weicht ab: gemerkt
    geraet(false); // Geraet jetzt auch hell
    farbschema.umschalten(); // dunkel, weicht ab
    farbschema.umschalten(); // hell = Geraet: Wahl geloescht
    geraet(true);
    expect(farbschema.dunkel()).toBeTrue();
  });

  it('folgt einem Wechsel am Geraet nicht, solange eine Wahl gemerkt ist', () => {
    const farbschema = dienst();
    farbschema.umschalten(); // dunkel, gemerkt
    geraet(false);
    expect(farbschema.dunkel()).toBeTrue();
  });

  it('zieht nach, wenn ein anderer Tab umschaltet oder die Wahl loescht', () => {
    const farbschema = dienst();
    andererTab('dark');
    expect(farbschema.dunkel()).toBeTrue();
    expect(attribut()).toBe('dark');

    andererTab(null);
    expect(farbschema.dunkel()).toBeFalse();
    expect(attribut()).toBe('light');
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
