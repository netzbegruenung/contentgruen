import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { Router, provideRouter } from '@angular/router';
import { AuthService } from './auth.service';
import { ANLASS_PARAM } from './anmeldeanlass';

@Component({ standalone: true, template: '' })
class LeerComponent {}

/**
 * Anmelden aus einer Seite heraus (Snackbar "Anmelden" nach dem Daumen, Persona-Test):
 * Danach geht es auf dieselbe Seite samt Suche zurueck, nicht auf die Startseite.
 */
describe('AuthService.login: Rueckkehrziel', () => {
  let service: AuthService;
  let router: Router;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([
          { path: 'result', component: LeerComponent },
          { path: 'login', component: LeerComponent },
          { path: 'search', component: LeerComponent },
        ]),
      ],
    });
    service = TestBed.inject(AuthService);
    router = TestBed.inject(Router);
  });

  function returnUrl(): string | null {
    return router.parseUrl(router.url).queryParamMap.get('returnUrl');
  }

  it('nimmt die jetzige Seite samt Suche als Rueckkehrziel', async () => {
    await router.navigateByUrl('/result?searchQuery=Windr%C3%A4der%20t%C3%B6ten%20V%C3%B6gel&typ=commentary');

    service.login();
    await new Promise((r) => setTimeout(r));

    expect(router.url.split('?')[0]).toBe('/login');
    const ziel = router.parseUrl(returnUrl()!);
    expect(ziel.root.children['primary'].segments.map((s) => s.path)).toEqual(['result']);
    expect(ziel.queryParamMap.get('searchQuery')).toBe('Windräder töten Vögel');
    expect(ziel.queryParamMap.get('typ')).toBe('commentary');
    expect(ziel.queryParamMap.has(ANLASS_PARAM)).toBeFalse();
  });

  it('haengt den Anlass ans Rueckkehrziel', async () => {
    await router.navigateByUrl('/result?searchQuery=Heizung');

    service.login('abstimmen');
    await new Promise((r) => setTimeout(r));

    const ziel = router.parseUrl(returnUrl()!);
    expect(ziel.queryParamMap.get('searchQuery')).toBe('Heizung');
    expect(ziel.queryParamMap.get(ANLASS_PARAM)).toBe('abstimmen');
  });

  it('bleibt auf der Login-Seite und behaelt deren Rueckkehrziel', async () => {
    await router.navigateByUrl('/login?returnUrl=%2Fresult%3FsearchQuery%3Dx');

    service.login('abstimmen');
    await new Promise((r) => setTimeout(r));

    expect(returnUrl()).toBe('/result?searchQuery=x');
  });
});
