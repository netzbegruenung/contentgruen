import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { Router } from '@angular/router';
import { AuthService } from './auth.service';
import { environment } from '../../environments/environment';
import { merkerSchluessel } from '../meine-beitraege/meilenstein-merker';

describe('AuthService', () => {
  let service: AuthService;
  let httpMock: HttpTestingController;
  let router: jasmine.SpyObj<Router>;

  const logoutUrl = `${environment.baseUrl}/api/auth/logout`;

  beforeEach(() => {
    const routerSpy = jasmine.createSpyObj('Router', ['navigate']);

    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [
        AuthService,
        { provide: Router, useValue: routerSpy }
      ]
    });

    service = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router) as jasmine.SpyObj<Router>;
  });

  afterEach(() => {
    httpMock.verify();
  });

  describe('logout', () => {
    it('entfernt den Merker der angezeigten Meilensteine des Kontos (#351)', () => {
      spyOn(console, 'error');
      service.setUserInfo({ isAuthenticated: true, userId: 'kim-1', userName: 'Kim', claims: null });
      localStorage.setItem(merkerSchluessel('kim-1'), '["einwurf-1"]');

      service.logout();
      httpMock.expectOne(logoutUrl).flush(null, { status: 500, statusText: 'Server Error' });

      expect(localStorage.getItem(merkerSchluessel('kim-1'))).toBeNull();
    });

    it('navigiert zur Startseite, wenn der Logout-Request fehlschlaegt', () => {
      spyOn(console, 'error');

      service.logout();

      httpMock.expectOne(logoutUrl).flush(
        { message: 'boom' },
        { status: 500, statusText: 'Server Error' }
      );

      expect(router.navigate).toHaveBeenCalledWith(['/']);
    });

    it('meldet den Nutzer im Fehlerfall auch lokal ab', () => {
      spyOn(console, 'error');

      service.logout();
      httpMock.expectOne(logoutUrl).flush(null, { status: 500, statusText: 'Server Error' });

      expect(service.getUserInfo()?.isAuthenticated).toBeFalse();
      expect(service.getUserInfo()?.userId).toBeNull();
    });

    it('fordert den Logout am BFF mit Cookies an', () => {
      service.logout();

      const req = httpMock.expectOne(logoutUrl);
      expect(req.request.method).toBe('POST');
      expect(req.request.withCredentials).toBeTrue();

      // Erfolgsfall nicht durchlaufen lassen: er setzt window.location.href und
      // wuerde den Karma-Runner navigieren.
      req.flush(null, { status: 500, statusText: 'Server Error' });
    });
  });
});
