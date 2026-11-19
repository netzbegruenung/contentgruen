import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ActivatedRouteSnapshot, Router, RouterStateSnapshot, UrlTree, provideRouter } from '@angular/router';
import { firstValueFrom, Observable } from 'rxjs';
import { AuthGuard, MIT_KONTO_VORSCHAU } from './auth.guard';
import { routes } from '../app.routes';

describe('AuthGuard', () => {
  let guard: AuthGuard;
  let http: HttpTestingController;
  let router: Router;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    });
    guard = TestBed.inject(AuthGuard);
    http = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
  });

  afterEach(() => http.verify());

  function pruefen(data: Record<string, unknown>, url: string, angemeldet: boolean): Promise<boolean | UrlTree> {
    const ergebnis = firstValueFrom(
      guard.canActivate({ data } as unknown as ActivatedRouteSnapshot, { url } as RouterStateSnapshot) as Observable<boolean | UrlTree>,
    );
    const anfrage = http.expectOne((r) => r.url.endsWith('/api/check-session'));
    if (angemeldet) anfrage.flush({});
    else anfrage.flush(null, { status: 401, statusText: 'Unauthorized' });
    return ergebnis;
  }

  it('lässt Angemeldete durch, auch an den Einstiegen ins Mitmachen', async () => {
    expect(await pruefen({ [MIT_KONTO_VORSCHAU]: true }, '/einwerfen', true)).toBeTrue();
  });

  it('zeigt Besuchern an den Einstiegen erst die Vorschau, mit dem Ziel', async () => {
    const baum = (await pruefen({ [MIT_KONTO_VORSCHAU]: true }, '/einwerfen?von=fangkorb', false)) as UrlTree;
    expect(router.serializeUrl(baum)).toBe('/mit-konto?ziel=%2Feinwerfen%3Fvon%3Dfangkorb');
  });

  it('führt Besucher auf anderen geschützten Seiten weiter direkt zur Anmeldung', async () => {
    const baum = (await pruefen({}, '/contributions', false)) as UrlTree;
    expect(router.serializeUrl(baum)).toBe('/login?returnUrl=%2Fcontributions');
  });

  it('markiert genau Einwerfen, Beitragen und Fangkorb als Einstiege mit Vorschau', () => {
    const markiert = routes.filter((r) => r.data?.[MIT_KONTO_VORSCHAU]).map((r) => r.path);
    expect(markiert.sort()).toEqual(['contribute', 'einwerfen', 'fangkorb']);
  });
});
