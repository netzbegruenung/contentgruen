import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { PublicGuard } from './public.guard';
import { AuthService } from './auth.service';
import { environment } from '../../environments/environment';
import { of, throwError } from 'rxjs';

describe('PublicGuard', () => {
  let guard: PublicGuard;
  let httpMock: HttpTestingController;
  let authService: jasmine.SpyObj<AuthService>;

  beforeEach(() => {
    const authServiceSpy = jasmine.createSpyObj('AuthService', ['fetchUserInfo', 'setUserInfo']);

    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [
        PublicGuard,
        { provide: AuthService, useValue: authServiceSpy }
      ]
    });

    guard = TestBed.inject(PublicGuard);
    httpMock = TestBed.inject(HttpTestingController);
    authService = TestBed.inject(AuthService) as jasmine.SpyObj<AuthService>;
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should allow access for authenticated users', (done) => {
    authService.fetchUserInfo.and.returnValue(of({
      isAuthenticated: true,
      userId: 'user123',
      userName: 'Test User',
      claims: {}
    }));

    guard.canActivate().subscribe(result => {
      expect(result).toBe(true);
      expect(authService.fetchUserInfo).toHaveBeenCalled();
      done();
    });

    const req = httpMock.expectOne(`${environment.baseUrl}/api/check-session`);
    req.flush({});
  });

  it('should allow access for anonymous users', (done) => {
    guard.canActivate().subscribe(result => {
      expect(result).toBe(true);
      expect(authService.setUserInfo).toHaveBeenCalledWith({
        isAuthenticated: false,
        userId: null,
        userName: null,
        claims: null
      });
      done();
    });

    const req = httpMock.expectOne(`${environment.baseUrl}/api/check-session`);
    req.flush(null, { status: 401, statusText: 'Unauthorized' });
  });

  it('should handle network errors gracefully', (done) => {
    guard.canActivate().subscribe(result => {
      expect(result).toBe(true);
      expect(authService.setUserInfo).toHaveBeenCalledWith({
        isAuthenticated: false,
        userId: null,
        userName: null,
        claims: null
      });
      done();
    });

    const req = httpMock.expectOne(`${environment.baseUrl}/api/check-session`);
    req.error(new ErrorEvent('Network error'));
  });
});
