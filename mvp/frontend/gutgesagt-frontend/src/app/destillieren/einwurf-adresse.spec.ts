import { Location } from '@angular/common';
import { provideLocationMocks } from '@angular/common/testing';
import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';

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
