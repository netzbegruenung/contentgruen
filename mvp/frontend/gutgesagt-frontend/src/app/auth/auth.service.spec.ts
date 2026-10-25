import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { Router } from '@angular/router';
import { AuthService } from './auth.service';
import { SessionService } from '../services/session.service';
import { environment } from '../../environments/environment';

describe('AuthService', () => {
  let service: AuthService;
  let httpMock: HttpTestingController;
  let sessionService: jasmine.SpyObj<SessionService>;
  let router: jasmine.SpyObj<Router>;

  const logoutUrl = `${environment.baseUrl}/api/auth/logout`;

  beforeEach(() => {
    const sessionServiceSpy = jasmine.createSpyObj('SessionService', [
      'getSessionId',
      'regenerateSessionId',
      'clearSessionId'
    ]);
    const routerSpy = jasmine.createSpyObj('Router', ['navigate']);

    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [
        AuthService,
        { provide: SessionService, useValue: sessionServiceSpy },
        { provide: Router, useValue: routerSpy }
      ]
    });

    service = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
    sessionService = TestBed.inject(SessionService) as jasmine.SpyObj<SessionService>;
    router = TestBed.inject(Router) as jasmine.SpyObj<Router>;
  });

  afterEach(() => {
    httpMock.verify();
  });

  describe('logout', () => {
    // Der Fehlerfall ist der wichtigere Test: er navigiert nur, statt die Seite
    // neu zu laden. Ohne die Neuvergabe behielten laufende Dienste dort die alte
    // Session-ID und truegen sie ueber die Abmeldung hinweg weiter.
    it('vergibt die Session-ID neu, wenn der Logout-Request fehlschlaegt', () => {
      spyOn(console, 'error');

      service.logout();

      httpMock.expectOne(logoutUrl).flush(
        { message: 'boom' },
        { status: 500, statusText: 'Server Error' }
      );

      expect(sessionService.regenerateSessionId).toHaveBeenCalledTimes(1);
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
      expect(sessionService.regenerateSessionId).toHaveBeenCalled();
    });
  });
});
