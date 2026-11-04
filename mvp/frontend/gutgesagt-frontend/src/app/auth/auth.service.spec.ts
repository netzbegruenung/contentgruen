import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { Router } from '@angular/router';
import { AuthService } from './auth.service';
import { environment } from '../../environments/environment';

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
