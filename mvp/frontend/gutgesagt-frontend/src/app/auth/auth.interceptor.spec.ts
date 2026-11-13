import { TestBed, fakeAsync, tick } from '@angular/core/testing';
import { HttpClient, HttpErrorResponse, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Router } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Subject } from 'rxjs';
import { AuthInterceptor } from './auth.interceptor';
import { stillerKontext } from '../shared/selbst-nachladen';

describe('AuthInterceptor', () => {
  let httpClient: HttpClient;
  let httpMock: HttpTestingController;
  let router: jasmine.SpyObj<Router>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;
  let knopf: Subject<void>;

  beforeEach(() => {
    const routerSpy = jasmine.createSpyObj('Router', ['navigate']);
    knopf = new Subject<void>();
    snackBar = jasmine.createSpyObj('MatSnackBar', ['open']);
    snackBar.open.and.returnValue({ onAction: () => knopf.asObservable() } as any);

    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([AuthInterceptor])),
        provideHttpClientTesting(),
        { provide: Router, useValue: routerSpy },
        { provide: MatSnackBar, useValue: snackBar }
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

  it('leitet eine stille Hintergrund-Abfrage bei 401 nicht auf /login um', () => {
    let status = 0;
    httpClient.get('/api/v1/moderation/reports', { context: stillerKontext() }).subscribe({
      error: (error: HttpErrorResponse) => (status = error.status),
    });

    httpMock.expectOne('/api/v1/moderation/reports').flush(null, { status: 401, statusText: 'Unauthorized' });

    expect(status).toBe(401);
    expect(router.navigate).not.toHaveBeenCalled();
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

  it('zeigt bei fehlender Art.-9-Einwilligung einen Hinweis und bleibt auf der Seite (#489)', fakeAsync(() => {
    (router as any).url = '/einwerfen?von=fangkorb';
    httpClient.post('/api/v1/rawinput/addRawInput', {}).subscribe({ error: () => {} });

    httpMock
      .expectOne('/api/v1/rawinput/addRawInput')
      .flush({ detail: 'art9_einwilligung_fehlt' }, { status: 403, statusText: 'Forbidden' });
    tick();

    expect(snackBar.open).toHaveBeenCalledWith(jasmine.stringContaining('Einwilligung'), 'Einwilligen', jasmine.any(Object));
    expect(router.navigate).not.toHaveBeenCalled();
  }));

  it('oeffnet den Hinweis nach dem Fehlerzweig des Aufrufers, damit dessen Hinweis ihn nicht ersetzt', fakeAsync(() => {
    const reihenfolge: string[] = [];
    snackBar.open.and.callFake(((text: string) => {
      reihenfolge.push(text);
      return { onAction: () => knopf.asObservable() } as any;
    }) as any);
    httpClient.post('/api/v1/voting/content/1/like', {}).subscribe({ error: () => snackBar.open('Aufrufer') });
    httpMock
      .expectOne('/api/v1/voting/content/1/like')
      .flush({ detail: 'art9_einwilligung_fehlt' }, { status: 403, statusText: 'Forbidden' });
    tick();

    expect(reihenfolge).toEqual(['Aufrufer', jasmine.stringContaining('Einwilligung') as any]);
  }));

  it('fuehrt ueber den Knopf im Hinweis zur Einwilligung und zurueck', fakeAsync(() => {
    (router as any).url = '/einwerfen?von=fangkorb';
    httpClient.post('/api/v1/rawinput/addRawInput', {}).subscribe({ error: () => {} });
    httpMock
      .expectOne('/api/v1/rawinput/addRawInput')
      .flush({ detail: 'art9_einwilligung_fehlt' }, { status: 403, statusText: 'Forbidden' });
    tick();

    knopf.next();

    expect(router.navigate).toHaveBeenCalledWith(['/einwilligung'], {
      queryParams: { returnUrl: '/einwerfen?von=fangkorb' },
    });
  }));

  it('leitet bei anderem 403 nicht um', fakeAsync(() => {
    (router as any).url = '/einwerfen';
    httpClient.post('/api/v1/moderation/x', {}).subscribe({ error: () => {} });

    httpMock
      .expectOne('/api/v1/moderation/x')
      .flush({ detail: 'Admin privileges required' }, { status: 403, statusText: 'Forbidden' });
    tick();

    expect(snackBar.open).not.toHaveBeenCalled();
  }));

  it('fuehrt auf der Seite der Einwilligung selbst nicht noch einmal hin', fakeAsync(() => {
    (router as any).url = '/einwilligung?returnUrl=%2Feinwerfen';
    httpClient.post('/api/v1/rawinput/addRawInput', {}).subscribe({ error: () => {} });
    httpMock
      .expectOne('/api/v1/rawinput/addRawInput')
      .flush({ detail: 'art9_einwilligung_fehlt' }, { status: 403, statusText: 'Forbidden' });
    tick();

    knopf.next();

    expect(router.navigate).not.toHaveBeenCalled();
  }));

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
