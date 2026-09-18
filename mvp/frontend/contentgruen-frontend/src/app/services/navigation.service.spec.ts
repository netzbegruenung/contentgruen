import { TestBed, fakeAsync, tick } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';

import { NavigationService } from './navigation.service';
import { routes } from '../app.routes';
import { ohneWaechter } from '../testing/routen-ohne-waechter';

describe('NavigationService.goBack', () => {
  let router: Router;
  let service: NavigationService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideRouter(ohneWaechter(routes))],
    });
    router = TestBed.inject(Router);
    service = TestBed.inject(NavigationService);
  });

  /** Von ``start`` aus zurueck und schauen, wo man landet. */
  function zurueckVon(start: string): string {
    router.navigateByUrl(start);
    tick();
    service.goBack();
    tick();
    return router.url;
  }

  /**
   * Ein angemeldeter Hook, der erst faellt, wenn der Test es sagt - so laesst
   * sich pruefen, was waehrend des Speicherns passiert.
   */
  function haengenderHook(): {
    hook: () => Promise<void>;
    aufrufe: () => number;
    fertig: () => void;
    scheitern: () => void;
  } {
    let aufloesen: (() => void) | null = null;
    let ablehnen: ((grund: unknown) => void) | null = null;
    let aufrufe = 0;
    return {
      hook: () => {
        aufrufe++;
        return new Promise<void>((ja, nein) => {
          aufloesen = ja;
          ablehnen = nein;
        });
      },
      aufrufe: () => aufrufe,
      fertig: () => aufloesen?.(),
      scheitern: () => ablehnen?.(new Error('nicht gespeichert')),
    };
  }

  describe('Vorher-Erledigen und Doppel-Tipp', () => {
    it('ignoriert den zweiten Tipp, solange der erste laeuft', fakeAsync(() => {
      const { hook, aufrufe, fertig } = haengenderHook();
      router.navigateByUrl('/fangkorb');
      tick();
      service.registerBeforeBack(hook);

      service.goBack();
      tick();
      service.goBack();
      tick();

      // Der zweite Tipp faellt in die Sperre: kein zweiter Speicherlauf.
      expect(aufrufe()).toBe(1);
      expect(router.url).toBe('/fangkorb');

      fertig();
      tick();
      expect(router.url).toBe('/search');
    }));

    it('bleibt stehen, wenn das Vorher-Erledigen scheitert, und laesst danach wieder zu', fakeAsync(() => {
      const { hook, aufrufe, scheitern } = haengenderHook();
      router.navigateByUrl('/fangkorb');
      tick();
      service.registerBeforeBack(hook);

      service.goBack();
      tick();
      scheitern();
      tick();

      expect(router.url).toBe('/fangkorb');

      // Die Sperre ist wieder offen - ein erneuter Tipp ruft den Hook erneut.
      service.goBack();
      tick();
      expect(aufrufe()).toBe(2);
    }));

    it('laesst das Haus denselben Hook abwarten wie den Pfeil', fakeAsync(() => {
      const { hook, aufrufe, fertig } = haengenderHook();
      router.navigateByUrl('/destillieren/e-1');
      tick();
      service.registerBeforeBack(hook);

      service.navigateHome();
      tick();

      expect(aufrufe()).toBe(1);
      expect(router.url).toBe('/destillieren/e-1');

      fertig();
      tick();
      expect(router.url).toBe('/search');
    }));

    it('fuehrt das Haus zur Startseite, nicht eine Ebene hoeher', fakeAsync(() => {
      router.navigateByUrl('/destillieren/e-1');
      tick();

      service.navigateHome();
      tick();

      // Der Pfeil fuehrte von hier in den Fangkorb; das Haus geht nach Hause.
      expect(router.url).toBe('/search');
    }));
  });

  // Eine Zeile je Elternziel aus der Routentabelle.
  const ZUORDNUNGEN: ReadonlyArray<[string, string]> = [
    ['/result?searchQuery=Waermepumpe', '/search'],
    ['/contribute', '/search'],
    ['/fangkorb', '/search'],
    ['/contributions', '/search'],
    ['/login', '/search'],
    ['/about', '/search'],
    ['/impressum', '/search'],
    ['/datenschutz', '/search'],
    ['/nutzungsbedingungen', '/search'],
    ['/admin', '/search'],
    ['/admin/dashboard', '/search'],
    ['/admin/moderation', '/search'],
    // Aus dem Fangkorb-FAB kommt ?von=fangkorb dazu; siehe app.routes.spec.ts.
    ['/einwerfen', '/contribute'],
    ['/einwerfen?von=fangkorb', '/fangkorb'],
    ['/destillieren', '/fangkorb'],
    ['/destillieren/e-1', '/fangkorb'],
    ['/login/managed', '/login'],
    ['/workflow/add-commentary', '/contribute'],
    ['/workflow/add-generictext', '/contribute'],
    ['/workflow/add-image', '/contribute'],
  ];

  for (const [start, ziel] of ZUORDNUNGEN) {
    it(`fuehrt von ${start} nach ${ziel}`, fakeAsync(() => {
      expect(zurueckVon(start)).toBe(ziel);
    }));
  }

  it('fuehrt aus einem Formular im Destillier-Ablauf zurueck zum Einwurf', fakeAsync(() => {
    expect(zurueckVon('/workflow/add-commentary?rohinput=e-42')).toBe('/destillieren/e-42');
    expect(zurueckVon('/workflow/add-generictext?rohinput=e-7')).toBe('/destillieren/e-7');
  }));

  it('fuehrt ohne Elternziel auf die Startseite', fakeAsync(() => {
    // /search selbst traegt kein parent - und hat im Kopf auch keinen Pfeil.
    expect(zurueckVon('/search')).toBe('/search');
  }));

  it('nimmt immer dasselbe Ziel, unabhaengig vom Weg dorthin', fakeAsync(() => {
    router.navigateByUrl('/contributions');
    tick();
    router.navigateByUrl('/fangkorb');
    tick();
    router.navigateByUrl('/einwerfen');
    tick();

    service.goBack();
    tick();

    // History waere /fangkorb gewesen; der Pfeil nimmt trotzdem das Elternziel.
    expect(router.url).toBe('/contribute');

    router.navigateByUrl('/contributions');
    tick();
    router.navigateByUrl('/einwerfen');
    tick();
    service.goBack();
    tick();

    expect(router.url).toBe('/contribute');
  }));
});
