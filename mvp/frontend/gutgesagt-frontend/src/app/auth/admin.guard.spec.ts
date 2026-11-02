import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, Router, RouterStateSnapshot } from '@angular/router';
import { BehaviorSubject } from 'rxjs';
import { AdminGuard } from './admin.guard';
import { AuthService, UserInfo } from './auth.service';

/**
 * Design-Audit A5 (#512): Beim Direktaufruf oder Neuladen einer /admin-Adresse ist
 * userInfo$ noch leer (BehaviorSubject(null)); der Waechter las diesen ersten Wert
 * und schickte auch Admins auf die Anmeldeseite. Er wartet jetzt auf die Antwort.
 */
describe('AdminGuard', () => {
  let userInfo$: BehaviorSubject<UserInfo | null>;
  let router: jasmine.SpyObj<Router>;
  let guard: AdminGuard;
  const state = { url: '/admin/dashboard' } as RouterStateSnapshot;

  const ADMIN: UserInfo = { isAuthenticated: true, isAdmin: true, userId: 'u', userName: 'A', claims: {} };
  const NUTZER: UserInfo = { isAuthenticated: true, isAdmin: false, userId: 'u', userName: 'N', claims: {} };
  const BESUCHER: UserInfo = { isAuthenticated: false, userId: null, userName: null, claims: null };

  beforeEach(() => {
    userInfo$ = new BehaviorSubject<UserInfo | null>(null);
    router = jasmine.createSpyObj('Router', ['navigate']);
    TestBed.configureTestingModule({
      providers: [
        { provide: AuthService, useValue: { userInfo$: userInfo$.asObservable() } },
        { provide: Router, useValue: router },
      ],
    });
    guard = TestBed.inject(AdminGuard);
  });

  function pruefen(): boolean[] {
    const ergebnisse: boolean[] = [];
    guard.canActivate({} as ActivatedRouteSnapshot, state).subscribe((e) => ergebnisse.push(e));
    return ergebnisse;
  }

  it('entscheidet nicht, solange noch niemand weiss, wer angemeldet ist', () => {
    const ergebnisse = pruefen();

    expect(ergebnisse).toEqual([]);
    expect(router.navigate).not.toHaveBeenCalled();
  });

  it('laesst Admins durch, sobald die Antwort da ist', () => {
    const ergebnisse = pruefen();
    userInfo$.next(ADMIN);

    expect(ergebnisse).toEqual([true]);
    expect(router.navigate).not.toHaveBeenCalled();
  });

  it('schickt Besucher zur Anmeldung, mit Ruecksprung', () => {
    const ergebnisse = pruefen();
    userInfo$.next(BESUCHER);

    expect(ergebnisse).toEqual([false]);
    expect(router.navigate).toHaveBeenCalledWith(['/login'], { queryParams: { returnUrl: '/admin/dashboard' } });
  });

  it('schickt Angemeldete ohne Adminrecht auf die Startseite, nicht zur Anmeldung', () => {
    const ergebnisse = pruefen();
    userInfo$.next(NUTZER);

    expect(ergebnisse).toEqual([false]);
    expect(router.navigate).toHaveBeenCalledWith(['/search']);
  });

  it('entscheidet nur einmal, auch wenn sich die Anmeldung spaeter aendert', () => {
    const ergebnisse = pruefen();
    userInfo$.next(ADMIN);
    userInfo$.next(BESUCHER);

    expect(ergebnisse).toEqual([true]);
  });
});
