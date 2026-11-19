import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { convertToParamMap } from '@angular/router';

import { StatementService, VORSCHLAG_ANZAHL } from './statement.service';
import { environment } from '../../environments/environment';
import { NUR_LESEND } from '../auth/cache.interceptor';

describe('StatementService: Aussage eines Beitragsformulars', () => {
  let service: StatementService;
  let httpMock: HttpTestingController;

  const getByIdUrl = `${environment.baseUrl}/api/v1/statement/getById`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()]
    });
    service = TestBed.inject(StatementService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  describe('aussageAusAdresse', () => {
    it('laedt ?aussage= per ID', () => {
      let ergebnis: unknown;
      service.aussageAusAdresse(convertToParamMap({ aussage: 'a-1', searchQuery: 'egal' }))
        .subscribe((aussage) => (ergebnis = aussage));

      const anfrage = httpMock.expectOne((req) => req.url === getByIdUrl);
      expect(anfrage.request.params.get('statement_id')).toBe('a-1');
      anfrage.flush({ statement_id: 'a-1', statement_text: 'Text' });

      expect(ergebnis).toEqual({ statement_id: 'a-1', statement_text: 'Text' });
    });

    it('nimmt den Text aus ?searchQuery=, wenn die ID 404 gibt (Suchanfrage unter der Schwelle)', () => {
      let ergebnis: unknown;
      service.aussageAusAdresse(convertToParamMap({ aussage: 'a-1', searchQuery: '  Wer zahlt das  ' }))
        .subscribe((aussage) => (ergebnis = aussage));

      httpMock.expectOne((req) => req.url === getByIdUrl)
        .flush('Statement not found', { status: 404, statusText: 'Not Found' });

      expect(ergebnis).toEqual({ statement_id: '', statement_text: 'Wer zahlt das' });
    });

    it('meldet den Fehler weiter, wenn die ID 404 gibt und kein Text da ist', () => {
      let fehler: any;
      service.aussageAusAdresse(convertToParamMap({ aussage: 'a-1' }))
        .subscribe({ error: (e) => (fehler = e) });

      httpMock.expectOne((req) => req.url === getByIdUrl)
        .flush('Statement not found', { status: 404, statusText: 'Not Found' });

      expect(fehler?.status).toBe(404);
    });

    it('meldet andere Fehler weiter, auch mit Text', () => {
      let fehler: any;
      service.aussageAusAdresse(convertToParamMap({ aussage: 'a-1', searchQuery: 'Wer zahlt das' }))
        .subscribe({ error: (e) => (fehler = e) });

      httpMock.expectOne((req) => req.url === getByIdUrl)
        .flush('kaputt', { status: 500, statusText: 'Server Error' });

      expect(fehler?.status).toBe(500);
    });

    it('kuerzt eine lange ?searchQuery= auf 1000 Zeichen', () => {
      let ergebnis: any;
      service.aussageAusAdresse(convertToParamMap({ searchQuery: 'a'.repeat(1500) }))
        .subscribe((aussage) => (ergebnis = aussage));

      expect(ergebnis.statement_text.length).toBe(1000);
    });

    it('nimmt ?searchQuery= als Text ohne ID und ohne Aufruf', () => {
      let ergebnis: unknown;
      service.aussageAusAdresse(convertToParamMap({ searchQuery: '  Waermepumpen  ' }))
        .subscribe((aussage) => (ergebnis = aussage));

      expect(ergebnis).toEqual({ statement_id: '', statement_text: 'Waermepumpen' });
    });
  });
});

describe('StatementService: Vorschlaege im Antwort-auf-Feld', () => {
  let service: StatementService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()]
    });
    service = TestBed.inject(StatementService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('fragt Vorschlaege an, Schwelle und Widerspruch entscheidet der Suchdienst', () => {
    let ergebnis: unknown;
    service.aussageVorschlaege('Wärmepumpen teuer').subscribe((vorschlaege) => (ergebnis = vorschlaege));

    const anfrage = httpMock.expectOne(`${environment.baseUrl}/api/v1/statement/searchStatements`);
    expect(anfrage.request.body).toEqual({
      query_text: 'Wärmepumpen teuer',
      limit: VORSCHLAG_ANZAHL,
      nur_kuratiert: true,
      vorschlaege: true,
    });
    anfrage.flush({ results: [{ id: 'a-1', text: 'x', replysuggestions_count: 1, score: 0.7 }] });

    expect(ergebnis).toEqual([{ id: 'a-1', text: 'x', replysuggestions_count: 1, score: 0.7 }]);
  });

  it('laesst die Suche ohne Filter wie bisher', () => {
    service.searchStatements('klimaschutz', 1).subscribe();

    const anfrage = httpMock.expectOne(`${environment.baseUrl}/api/v1/statement/searchStatements`);
    expect(anfrage.request.body).toEqual({ query_text: 'klimaschutz', limit: 1 });
    anfrage.flush({ results: [] });
  });

  it('markiert die Aussagensuche als nur lesend, damit sie den Cache stehen laesst', () => {
    service.searchStatements('klimaschutz', 1).subscribe();

    const anfrage = httpMock.expectOne(`${environment.baseUrl}/api/v1/statement/searchStatements`);
    expect(anfrage.request.context.get(NUR_LESEND)).toBeTrue();
    anfrage.flush({ results: [] });
  });
});
