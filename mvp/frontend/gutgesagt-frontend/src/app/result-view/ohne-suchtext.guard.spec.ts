import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';

import { ohneSuchtextZumStart } from './ohne-suchtext.guard';
import { routes } from '../app.routes';

@Component({ standalone: true, template: '' })
class LeerComponent {}

/** /result ohne Suchtext geht auf den Start (#642, R50). */
describe('ohneSuchtextZumStart', () => {
  let router: Router;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([
          { path: 'search', component: LeerComponent },
          { path: 'result', component: LeerComponent, canActivate: [ohneSuchtextZumStart], runGuardsAndResolvers: 'paramsOrQueryParamsChange' },
        ]),
      ],
    });
    router = TestBed.inject(Router);
  });

  for (const adresse of ['/result', '/result?searchQuery=', '/result?searchQuery=%20%20']) {
    it(`leitet ${adresse} auf den Start`, async () => {
      const harness = await RouterTestingHarness.create();
      await harness.navigateByUrl(adresse);
      expect(router.url).toBe('/search');
    });
  }

  it('laesst eine Suche mit Text durch', async () => {
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/result?searchQuery=Tempolimit');
    expect(router.url).toBe('/result?searchQuery=Tempolimit');
  });

  it('leitet auch auf den Start, wenn auf der Ergebnisseite der Text wegfaellt', async () => {
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/result?searchQuery=Tempolimit');
    await harness.navigateByUrl('/result');
    expect(router.url).toBe('/search');
  });

  it('haengt in der echten Routentabelle an /result', () => {
    const result = routes.find((r) => r.path === 'result');
    expect(result?.canActivate).toContain(ohneSuchtextZumStart);
    expect(result?.runGuardsAndResolvers).toBe('paramsOrQueryParamsChange');
  });
});
