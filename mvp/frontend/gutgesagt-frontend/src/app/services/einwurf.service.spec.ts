import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { Einwurf, EinwurfService, EinwurfSeite } from './einwurf.service';
import { LoggingService } from './logging.service';
import { environment } from '../../environments/environment';
import { CONSENT_HINWEIS, CONSENT_HINWEIS_SATZ } from '../shared/consent-hinweis';

function einwurf(overrides: Partial<Einwurf> = {}): Einwurf {
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

describe('EinwurfService', () => {
  let service: EinwurfService;
  let httpMock: HttpTestingController;

  const basis = `${environment.baseUrl}/api/v1/rawinput`;

  beforeEach(() => {
    const loggingSpy = jasmine.createSpyObj('LoggingService', ['debug', 'error', 'warn']);

    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [EinwurfService, { provide: LoggingService, useValue: loggingSpy }],
    });

    service = TestBed.inject(EinwurfService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('schickt einen Einwurf an addRawInput, mit der Kennung des CC0-Hinweises', () => {
    service.einwerfen({ url: 'https://example.org/post' }).subscribe((antwort) => {
      expect(antwort.id).toBe('abc');
    });

    const anfrage = httpMock.expectOne(`${basis}/addRawInput`);
    expect(anfrage.request.method).toBe('POST');
    expect(anfrage.request.body).toEqual({
      url: 'https://example.org/post',
      cc0_wortlaut: CONSENT_HINWEIS.kennung,
    });
    anfrage.flush({ id: 'abc' });
  });

  it('holt den Fangkorb mit Seitenangaben', () => {
    const antwort: EinwurfSeite = {
      results_count: 0,
      results: [],
      total_records_count: 0,
    };

    service.fangkorbLaden(2, 50).subscribe((daten) => {
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

  it('holt die eigenen Einwuerfe mit Seitenangaben', () => {
    service.eigeneLaden(2, 24).subscribe();

    const anfrage = httpMock.expectOne((req) => req.url === `${basis}/getOwnRawInputs`);
    expect(anfrage.request.method).toBe('GET');
    expect(anfrage.request.params.get('page')).toBe('2');
    expect(anfrage.request.params.get('page_size')).toBe('24');
    anfrage.flush({ results_count: 0, results: [], total_records_count: 0 });
  });

  describe('Destillieren', () => {
    it('holt einen einzelnen Einwurf', () => {
      service.einwurfLaden('id-1').subscribe((daten) => expect(daten.id).toBe('id-1'));

      const anfrage = httpMock.expectOne(`${basis}/id-1`);
      expect(anfrage.request.method).toBe('GET');
      anfrage.flush(einwurf());
    });

    it('speichert den Satz per PUT, mit der Kennung des Hinweises beim Satz', () => {
      service.satzSpeichern('id-1', 'Mein Satz').subscribe();

      const anfrage = httpMock.expectOne(`${basis}/id-1/draft`);
      expect(anfrage.request.method).toBe('PUT');
      expect(anfrage.request.body).toEqual({
        sentence: 'Mein Satz',
        cc0_wortlaut: CONSENT_HINWEIS_SATZ.kennung,
      });
      anfrage.flush({ raw_input_id: 'id-1', sentence: 'Mein Satz', updated_at: null });
    });

    it('sichert den Satz per fetch mit keepalive', () => {
      const fetchSpy = spyOn(window, 'fetch').and.returnValue(Promise.resolve(new Response()));

      service.satzSpeichernKeepalive('id-1', 'Mein Satz');

      const [url, optionen] = fetchSpy.calls.mostRecent().args as [string, RequestInit];
      expect(url).toBe(`${basis}/id-1/draft`);
      expect(optionen.method).toBe('PUT');
      expect(optionen.keepalive).toBeTrue();
      expect(optionen.credentials).toBe('include');
      expect(JSON.parse(optionen.body as string)).toEqual({
        sentence: 'Mein Satz',
        cc0_wortlaut: CONSENT_HINWEIS_SATZ.kennung,
      });
    });

    it('verwirft per PATCH ohne content_id', () => {
      service.updateStatus('id-1', 'discarded').subscribe();

      const anfrage = httpMock.expectOne(`${basis}/id-1/status`);
      expect(anfrage.request.method).toBe('PATCH');
      expect(anfrage.request.body).toEqual({ status: 'discarded' });
      anfrage.flush(einwurf({ status: 'discarded' }));
    });

    it('verknuepft mit dem Beitrag und seinem Typ', () => {
      service.updateStatus('id-1', 'processed', 'beitrag-1', 'commentary').subscribe();

      const anfrage = httpMock.expectOne(`${basis}/id-1/status`);
      expect(anfrage.request.body).toEqual({
        status: 'processed',
        content_id: 'beitrag-1',
        content_type: 'commentary',
      });
      anfrage.flush(einwurf({ status: 'processed' }));
    });

    it('laesst den Typ weg, wenn keiner bekannt ist', () => {
      service.updateStatus('id-1', 'processed', 'beitrag-1').subscribe();

      const anfrage = httpMock.expectOne(`${basis}/id-1/status`);
      expect(anfrage.request.body).toEqual({ status: 'processed', content_id: 'beitrag-1' });
      anfrage.flush(einwurf({ status: 'processed' }));
    });

    it('bietet als naechstes nur offene Einwuerfe ohne eigenen Satz an', () => {
      let naechster: Einwurf | null | undefined;
      service.naechsterOffenerEinwurf('id-aktuell').subscribe((e) => (naechster = e));

      httpMock.expectOne((req) => req.url === `${basis}/getRawInputs`).flush({
        results_count: 5,
        total_records_count: 5,
        results: [
          einwurf({ id: 'id-aktuell' }),
          einwurf({ id: 'id-verworfen', status: 'discarded' }),
          einwurf({ id: 'id-spaeter', own_draft: 'zurueckgestellt' }),
          einwurf({ id: 'id-ausformuliert', status: 'processed' }),
          einwurf({ id: 'id-naechster' }),
        ],
      });

      expect(naechster?.id).toBe('id-naechster');
    });

    it('bietet auch Destilliertes an, solange es keinen eigenen Satz gibt', () => {
      let naechster: Einwurf | null | undefined;
      service.naechsterOffenerEinwurf().subscribe((e) => (naechster = e));

      httpMock.expectOne((req) => req.url === `${basis}/getRawInputs`).flush({
        results_count: 2,
        total_records_count: 2,
        results: [
          einwurf({ id: 'id-eigener-satz', status: 'in_progress', own_draft: 'meiner' }),
          einwurf({ id: 'id-fremder-satz', status: 'in_progress' }),
        ],
      });

      expect(naechster?.id).toBe('id-fremder-satz');
    });

    it('bietet in dieser Runde Zurueckgestelltes nicht wieder an - auch ohne Satz', () => {
      // Zwei offene Einwuerfe ohne Satz: "Spaeter" auf A, dann auf B. Frueher
      // bot die zweite Abfrage wieder A an, und so fort.
      const liste = {
        results_count: 2,
        total_records_count: 2,
        results: [einwurf({ id: 'id-a' }), einwurf({ id: 'id-b' })],
      };
      let naechster: Einwurf | null | undefined;

      service.zurueckstellen('id-a');
      service.naechsterOffenerEinwurf('id-a').subscribe((e) => (naechster = e));
      httpMock.expectOne((req) => req.url === `${basis}/getRawInputs`).flush(liste);
      expect(naechster?.id).toBe('id-b');

      service.zurueckstellen('id-b');
      service.naechsterOffenerEinwurf('id-b').subscribe((e) => (naechster = e));
      httpMock.expectOne((req) => req.url === `${basis}/getRawInputs`).flush(liste);
      expect(naechster).toBeNull();
    });

    it('bietet nach neuer Runde Zurueckgestelltes wieder an', () => {
      let naechster: Einwurf | null | undefined;
      service.zurueckstellen('id-a');

      service.rundeBeginnen();
      service.naechsterOffenerEinwurf().subscribe((e) => (naechster = e));
      httpMock.expectOne((req) => req.url === `${basis}/getRawInputs`).flush({
        results_count: 1,
        total_records_count: 1,
        results: [einwurf({ id: 'id-a' })],
      });

      expect(naechster?.id).toBe('id-a');
    });

    it('meldet null, wenn nichts mehr offen ist', () => {
      let naechster: Einwurf | null | undefined;
      service.naechsterOffenerEinwurf().subscribe((e) => (naechster = e));

      httpMock.expectOne((req) => req.url === `${basis}/getRawInputs`).flush({
        results_count: 1,
        total_records_count: 1,
        results: [einwurf({ status: 'processed' })],
      });

      expect(naechster).toBeNull();
    });
  });

  describe('gleicher Link (#263)', () => {
    it('fragt den Fangkorb nach Einwuerfen mit gleichem Link', () => {
      let gefunden: Einwurf[] | undefined;
      service.mitGleichemLink('https://example.org/a?x=1&y=2').subscribe((e) => (gefunden = e));

      const anfrage = httpMock.expectOne(`${basis}/gleicherLink`);
      expect(anfrage.request.method).toBe('POST');
      expect(anfrage.request.body).toEqual({ url: 'https://example.org/a?x=1&y=2' });
      anfrage.flush({ results: [einwurf({ status: 'processed' })] });

      expect(gefunden?.map((e) => e.status)).toEqual(['processed']);
    });
  });
});
