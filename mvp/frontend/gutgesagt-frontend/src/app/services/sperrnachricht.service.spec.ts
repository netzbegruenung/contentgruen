import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { SperrnachrichtService } from './sperrnachricht.service';
import { environment } from '../../environments/environment';

describe('SperrnachrichtService', () => {
  let service: SperrnachrichtService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(SperrnachrichtService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('liest die eigenen Sperrnachrichten, ohne Kennung in der Adresse', () => {
    let ergebnis: unknown;
    service.meine().subscribe((n) => (ergebnis = n));

    const req = httpMock.expectOne(`${environment.baseUrl}/api/v1/sperren/meine`);
    expect(req.request.method).toBe('GET');
    req.flush({ sperren: [] });

    expect(ergebnis).toEqual([]);
  });

  it('widerspricht per POST, leerer Text wird null', () => {
    service.widersprechen('sperre-1', '   ').subscribe();

    const req = httpMock.expectOne(`${environment.baseUrl}/api/v1/sperren/sperre-1/widerspruch`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ text: null });
    req.flush({ success: true });
  });

  it('widerspricht mit Text ohne Leerraum am Rand', () => {
    service.widersprechen('sperre-1', ' Das ist belegt. ').subscribe();

    const req = httpMock.expectOne(`${environment.baseUrl}/api/v1/sperren/sperre-1/widerspruch`);
    expect(req.request.body).toEqual({ text: 'Das ist belegt.' });
    req.flush({ success: true });
  });
});
