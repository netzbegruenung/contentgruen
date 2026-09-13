import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { RawInput, RawInputService, GetRawInputsResponse } from './raw-input.service';
import { LoggingService } from './logging.service';
import { cacheService } from '../auth/cache.interceptor';
import { environment } from '../../environments/environment';

function einwurf(overrides: Partial<RawInput> = {}): RawInput {
  return {
    id: 'id-1',
    content: 'ein Satz',
    url: null,
    image_url: null,
    submitted_by: 'testuser',
    source_channel: 'web',
    status: 'open',
    created_at: '2026-08-19T12:00:00Z',
    own_draft: null,
    ...overrides,
  };
}

describe('RawInputService', () => {
  let service: RawInputService;
  let httpMock: HttpTestingController;

  const basis = `${environment.baseUrl}/api/v1/rawinput`;

  beforeEach(() => {
    const loggingSpy = jasmine.createSpyObj('LoggingService', ['debug', 'error', 'warn']);

    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [RawInputService, { provide: LoggingService, useValue: loggingSpy }],
    });

    service = TestBed.inject(RawInputService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('schickt einen Einwurf an addRawInput', () => {
    service.addRawInput({ url: 'https://example.org/post' }).subscribe((antwort) => {
      expect(antwort.id).toBe('abc');
    });

    const anfrage = httpMock.expectOne(`${basis}/addRawInput`);
    expect(anfrage.request.method).toBe('POST');
    expect(anfrage.request.body).toEqual({ url: 'https://example.org/post' });
    anfrage.flush({ id: 'abc' });
  });

  it('holt den Fangkorb mit Seitenangaben', () => {
    const antwort: GetRawInputsResponse = {
      results_count: 0,
      results: [],
      total_records_count: 0,
    };

    service.getRawInputs(2, 50).subscribe((daten) => {
      expect(daten).toEqual(antwort);
    });

    const anfrage = httpMock.expectOne(
      (req) => req.url === `${basis}/getRawInputs`,
    );
    expect(anfrage.request.method).toBe('GET');
    expect(anfrage.request.params.get('page')).toBe('2');
    expect(anfrage.request.params.get('page_size')).toBe('50');
    anfrage.flush(antwort);
  });

  describe('Destillieren', () => {
    it('holt einen einzelnen Einwurf', () => {
      service.getRawInput('id-1').subscribe((daten) => expect(daten.id).toBe('id-1'));

      const anfrage = httpMock.expectOne(`${basis}/id-1`);
      expect(anfrage.request.method).toBe('GET');
      anfrage.flush(einwurf());
    });

    it('speichert den Entwurf per PUT und leert danach den Fangkorb-Cache', () => {
      const leeren = spyOn(cacheService, 'delete');

      service.saveDraft('id-1', 'Mein Satz').subscribe();

      const anfrage = httpMock.expectOne(`${basis}/id-1/draft`);
      expect(anfrage.request.method).toBe('PUT');
      expect(anfrage.request.body).toEqual({ sentence: 'Mein Satz' });
      expect(leeren).not.toHaveBeenCalled();
      anfrage.flush({ raw_input_id: 'id-1', sentence: 'Mein Satz', updated_at: null });
      expect(leeren).toHaveBeenCalledWith('/api/v1/rawinput');
    });

    it('sichert den Entwurf per fetch mit keepalive', () => {
      const fetchSpy = spyOn(window, 'fetch').and.returnValue(Promise.resolve(new Response()));

      service.saveDraftKeepalive('id-1', 'Mein Satz');

      const [url, optionen] = fetchSpy.calls.mostRecent().args as [string, RequestInit];
      expect(url).toBe(`${basis}/id-1/draft`);
      expect(optionen.method).toBe('PUT');
      expect(optionen.keepalive).toBeTrue();
      expect(optionen.credentials).toBe('include');
      expect(JSON.parse(optionen.body as string)).toEqual({ sentence: 'Mein Satz' });
    });

    it('verwirft per PATCH ohne content_id', () => {
      const leeren = spyOn(cacheService, 'delete');

      service.updateStatus('id-1', 'discarded').subscribe();

      const anfrage = httpMock.expectOne(`${basis}/id-1/status`);
      expect(anfrage.request.method).toBe('PATCH');
      expect(anfrage.request.body).toEqual({ status: 'discarded' });
      anfrage.flush(einwurf({ status: 'discarded' }));
      expect(leeren).toHaveBeenCalledWith('/api/v1/rawinput');
    });

    it('markiert als verarbeitet mit dem entstandenen Beitrag', () => {
      service.updateStatus('id-1', 'processed', 'beitrag-1').subscribe();

      const anfrage = httpMock.expectOne(`${basis}/id-1/status`);
      expect(anfrage.request.body).toEqual({ status: 'processed', content_id: 'beitrag-1' });
      anfrage.flush(einwurf({ status: 'processed' }));
    });

    it('bietet als naechstes nur offene Einwuerfe ohne eigenen Entwurf an', () => {
      let naechster: RawInput | null | undefined;
      service.naechsterOffenerEinwurf('id-aktuell').subscribe((e) => (naechster = e));

      httpMock.expectOne((req) => req.url === `${basis}/getRawInputs`).flush({
        results_count: 5,
        total_records_count: 5,
        results: [
          einwurf({ id: 'id-aktuell' }),
          einwurf({ id: 'id-verworfen', status: 'discarded' }),
          einwurf({ id: 'id-spaeter', own_draft: 'zurueckgestellt' }),
          einwurf({ id: 'id-verarbeitet', status: 'processed' }),
          einwurf({ id: 'id-naechster' }),
        ],
      });

      expect(naechster?.id).toBe('id-naechster');
    });

    it('meldet null, wenn nichts mehr offen ist', () => {
      let naechster: RawInput | null | undefined;
      service.naechsterOffenerEinwurf().subscribe((e) => (naechster = e));

      httpMock.expectOne((req) => req.url === `${basis}/getRawInputs`).flush({
        results_count: 1,
        total_records_count: 1,
        results: [einwurf({ status: 'processed' })],
      });

      expect(naechster).toBeNull();
    });
  });
});
