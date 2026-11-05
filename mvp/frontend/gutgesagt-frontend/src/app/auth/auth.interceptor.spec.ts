import { TestBed } from '@angular/core/testing';
import { HttpClient, HttpErrorResponse, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Router } from '@angular/router';
import { AuthInterceptor } from './auth.interceptor';

describe('AuthInterceptor', () => {
  let httpClient: HttpClient;
  let httpMock: HttpTestingController;
  let router: jasmine.SpyObj<Router>;

  beforeEach(() => {
    const routerSpy = jasmine.createSpyObj('Router', ['navigate']);

    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([AuthInterceptor])),
        provideHttpClientTesting(),
        { provide: Router, useValue: routerSpy }
      ]
    });

    httpClient = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router) as jasmine.SpyObj<Router>;
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should include withCredentials in all requests', () => {
    httpClient.get('/api/test').subscribe();

    const req = httpMock.expectOne('/api/test');
    expect(req.request.withCredentials).toBe(true);
    req.flush({});
  });

  it('should NOT redirect to login for 401 on public search endpoints', () => {
    httpClient.post('/api/v1/search/searchByText', {}).subscribe({
      error: (error: HttpErrorResponse) => {
        expect(error.status).toBe(401);
      }
    });

    const req = httpMock.expectOne('/api/v1/search/searchByText');
    req.flush(null, { status: 401, statusText: 'Unauthorized' });

    expect(router.navigate).not.toHaveBeenCalled();
  });

  it('should NOT redirect to login for 401 on metrics endpoint', () => {
    httpClient.get('/api/metrics').subscribe({
      error: (error: HttpErrorResponse) => {
        expect(error.status).toBe(401);
      }
    });

    const req = httpMock.expectOne('/api/metrics');
    req.flush(null, { status: 401, statusText: 'Unauthorized' });

    expect(router.navigate).not.toHaveBeenCalled();
  });

  // Design-Audit A6 (#512): Ein falsches Passwort warf aus dem Formular zurueck
  // auf die Login-Auswahl. Ein 401 der Anmeldung ist eine Antwort, kein Anlass.
  it('bleibt bei einem 401 der Anmeldung selbst auf der Seite', () => {
    httpClient.post('/api/auth/login/managed', {}).subscribe({ error: () => {} });

    httpMock.expectOne('/api/auth/login/managed').flush(null, { status: 401, statusText: 'Unauthorized' });

    expect(router.navigate).not.toHaveBeenCalled();
  });

  it('should redirect to login for 401 on protected endpoints', () => {
    httpClient.get('/api/v1/content/mycontents').subscribe({
      error: (error: HttpErrorResponse) => {
        expect(error.status).toBe(401);
      }
    });

    const req = httpMock.expectOne('/api/v1/content/mycontents');
    req.flush(null, { status: 401, statusText: 'Unauthorized' });

    expect(router.navigate).toHaveBeenCalledWith(['/login'], { queryParams: { returnUrl: jasmine.any(String) } });
  });

  it('should redirect to login for 401 on contribute endpoint', () => {
    httpClient.post('/api/v1/content/contribute', {}).subscribe({
      error: (error: HttpErrorResponse) => {
        expect(error.status).toBe(401);
      }
    });

    const req = httpMock.expectOne('/api/v1/content/contribute');
    req.flush(null, { status: 401, statusText: 'Unauthorized' });

    expect(router.navigate).toHaveBeenCalledWith(['/login'], { queryParams: { returnUrl: jasmine.any(String) } });
  });

  it('should pass through non-401 errors without redirecting', () => {
    httpClient.get('/api/test').subscribe({
      error: (error: HttpErrorResponse) => {
        expect(error.status).toBe(500);
      }
    });

    const req = httpMock.expectOne('/api/test');
    req.flush(null, { status: 500, statusText: 'Internal Server Error' });

    expect(router.navigate).not.toHaveBeenCalled();
  });

  it('fuehrt bei fehlender Art.-9-Einwilligung auf /einwilligung und zurueck (#489)', () => {
    (router as any).url = '/einwerfen?von=fangkorb';
    httpClient.post('/api/v1/rawinput/addRawInput', {}).subscribe({ error: () => {} });

    httpMock
      .expectOne('/api/v1/rawinput/addRawInput')
      .flush({ detail: 'art9_einwilligung_fehlt' }, { status: 403, statusText: 'Forbidden' });

    expect(router.navigate).toHaveBeenCalledWith(['/einwilligung'], {
      queryParams: { returnUrl: '/einwerfen?von=fangkorb' },
    });
  });

  it('leitet bei anderem 403 nicht um', () => {
    (router as any).url = '/einwerfen';
    httpClient.post('/api/v1/moderation/x', {}).subscribe({ error: () => {} });

    httpMock
      .expectOne('/api/v1/moderation/x')
      .flush({ detail: 'Admin privileges required' }, { status: 403, statusText: 'Forbidden' });

    expect(router.navigate).not.toHaveBeenCalled();
  });

  it('leitet auf der Seite der Einwilligung selbst nicht noch einmal um', () => {
    (router as any).url = '/einwilligung?returnUrl=%2Feinwerfen';
    httpClient.post('/api/v1/rawinput/addRawInput', {}).subscribe({ error: () => {} });

    httpMock
      .expectOne('/api/v1/rawinput/addRawInput')
      .flush({ detail: 'art9_einwilligung_fehlt' }, { status: 403, statusText: 'Forbidden' });

    expect(router.navigate).not.toHaveBeenCalled();
  });

  it('should handle successful requests without intervention', () => {
    const testData = { message: 'success' };

    httpClient.get('/api/test').subscribe(data => {
      expect(data).toEqual(testData);
    });

    const req = httpMock.expectOne('/api/test');
    req.flush(testData);

    expect(router.navigate).not.toHaveBeenCalled();
  });
});
