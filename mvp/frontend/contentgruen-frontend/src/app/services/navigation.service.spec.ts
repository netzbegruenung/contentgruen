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
    ['/einwerfen', '/fangkorb'],
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

    // History waere /fangkorb gewesen - das ist hier zufaellig dasselbe.
    // Entscheidend: aus /einwerfen fuehrt der Pfeil immer in den Fangkorb.
    expect(router.url).toBe('/fangkorb');

    router.navigateByUrl('/contributions');
    tick();
    router.navigateByUrl('/einwerfen');
    tick();
    service.goBack();
    tick();

    expect(router.url).toBe('/fangkorb');
  }));
});
