import { Location } from '@angular/common';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideLocationMocks } from '@angular/common/testing';
import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';

import { AuthGuard } from '../auth/auth.guard';
import { EINWURF_PARAM, alteEinwurfAdresseUmleiten } from './einwurf-adresse';

@Component({ standalone: true, template: '' })
class FormularStub {}

describe('Adressparameter fuer Einwuerfe', () => {
  let harness: RouterTestingHarness;
  let router: Router;
  let location: Location;

  beforeEach(async () => {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([
          { path: 'start', component: FormularStub },
          { path: 'workflow/add-commentary', component: FormularStub, canActivate: [alteEinwurfAdresseUmleiten] },
        ]),
        provideLocationMocks(),
      ],
    });
    harness = await RouterTestingHarness.create();
    router = TestBed.inject(Router);
    location = TestBed.inject(Location);
  });

  it('heisst nach dem Glossar', () => {
    expect(EINWURF_PARAM).toBe('einwurf');
  });

  it('laesst neue Adressen unveraendert', async () => {
    await harness.navigateByUrl('/workflow/add-commentary?einwurf=e-42');

    expect(router.url).toBe('/workflow/add-commentary?einwurf=e-42');
  });

  /**
   * Geteilte Adressen und die zuletzt offene Seite der installierten App tragen
   * noch den alten Namen. Sie oeffnen weiter dasselbe Formular zum selben Einwurf.
   */
  it('leitet alte Adressen auf den neuen Namen um und behaelt die uebrigen Parameter', async () => {
    await harness.navigateByUrl('/workflow/add-commentary?rohinput=e-42&tab=offen'); // retired-ok: alte Adresse

    expect(router.url).toBe('/workflow/add-commentary?tab=offen&einwurf=e-42');
  });

  it('haengt fuer die Umleitung keinen Schritt in der History an', async () => {
    await harness.navigateByUrl('/start');
    await harness.navigateByUrl('/workflow/add-commentary?rohinput=e-42'); // retired-ok: alte Adresse

    location.back();
    await harness.fixture.whenStable();

    expect(location.path()).toBe('/start');
  });

  it('nimmt bei beiden Namen den neuen', async () => {
    await harness.navigateByUrl('/workflow/add-commentary?rohinput=alt&einwurf=neu'); // retired-ok: alte Adresse

    expect(router.url).toBe('/workflow/add-commentary?einwurf=neu');
  });
});

/**
 * Ein Lesezeichen oder geteilter Link mit dem alten Namen, ohne Anmeldung: Der Login
 * soll mit der neuen Adresse zurueckfuehren. Das haengt daran, dass der Umleit-Guard
 * vor dem AuthGuard steht und dessen Weiterleitung zum Login abloest.
 */
describe('Alte Einwurf-Adresse ohne Anmeldung', () => {
  let harness: RouterTestingHarness;
  let router: Router;
  let http: HttpTestingController;

  beforeEach(async () => {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([
          { path: 'login', component: FormularStub },
          {
            path: 'workflow/add-commentary',
            component: FormularStub,
            canActivate: [alteEinwurfAdresseUmleiten, AuthGuard],
          },
        ]),
        provideLocationMocks(),
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    });
    harness = await RouterTestingHarness.create();
    router = TestBed.inject(Router);
    http = TestBed.inject(HttpTestingController);
  });

  it('fuehrt nach dem Login zur neuen Adresse zurueck', async () => {
    const navigation = router.navigateByUrl('/workflow/add-commentary?rohinput=e-42'); // retired-ok: alte Adresse
    await new Promise((weiter) => setTimeout(weiter));
    for (const anfrage of http.match((req) => req.url.endsWith('/api/check-session'))) {
      if (!anfrage.cancelled) {
        anfrage.flush(null, { status: 401, statusText: 'Unauthorized' });
      }
    }
    await navigation;
    await harness.fixture.whenStable();

    const ziel = router.parseUrl(router.url);
    expect(ziel.root.children['primary'].segments.map((s) => s.path)).toEqual(['login']);
    expect(ziel.queryParams['returnUrl']).toBe('/workflow/add-commentary?einwurf=e-42');
  });
});
