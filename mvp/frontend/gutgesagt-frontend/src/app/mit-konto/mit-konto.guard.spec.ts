import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ActivatedRouteSnapshot, Router, RouterStateSnapshot, UrlTree, convertToParamMap, provideRouter } from '@angular/router';
import { Observable, firstValueFrom } from 'rxjs';
import { AuthService } from '../auth/auth.service';
import { mitKontoVorschauGuard } from './mit-konto.guard';

describe('mitKontoVorschauGuard', () => {
  let http: HttpTestingController;
  let auth: jasmine.SpyObj<AuthService>;

  beforeEach(() => {
    auth = jasmine.createSpyObj<AuthService>('AuthService', ['setUserInfo']);
    TestBed.configureTestingModule({
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting(), { provide: AuthService, useValue: auth }],
    });
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  function pruefen(query: Record<string, string>, angemeldet: boolean): Promise<boolean | UrlTree> {
    const snapshot = { queryParamMap: convertToParamMap(query) } as ActivatedRouteSnapshot;
    const ergebnis = firstValueFrom(
      TestBed.runInInjectionContext(() => mitKontoVorschauGuard(snapshot, {} as RouterStateSnapshot)) as Observable<boolean | UrlTree>,
    );
    const anfrage = http.expectOne((r) => r.url.endsWith('/api/check-session'));
    if (angemeldet) anfrage.flush({});
    else anfrage.flush(null, { status: 401, statusText: 'Unauthorized' });
    return ergebnis;
  }

  it('schickt Angemeldete sofort zum Ziel, ohne die Vorschau zu zeigen', async () => {
    const baum = (await pruefen({ ziel: '/einwerfen?von=fangkorb' }, true)) as UrlTree;
    expect(TestBed.inject(Router).serializeUrl(baum)).toBe('/einwerfen?von=fangkorb');
  });

  it('schickt Angemeldete ohne gültiges Ziel nach Beitragen', async () => {
    const baum = (await pruefen({ ziel: '//fremd.example' }, true)) as UrlTree;
    expect(TestBed.inject(Router).serializeUrl(baum)).toBe('/contribute');
  });

  it('zeigt Besuchern die Vorschau und setzt sie als Besucher', async () => {
    expect(await pruefen({ ziel: '/einwerfen' }, false)).toBeTrue();
    expect(auth.setUserInfo).toHaveBeenCalledWith(jasmine.objectContaining({ isAuthenticated: false }));
  });
});
