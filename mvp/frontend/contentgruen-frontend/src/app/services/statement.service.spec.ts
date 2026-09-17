import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { convertToParamMap } from '@angular/router';

import { StatementService, VORSCHLAG_ANZAHL, VORSCHLAG_MIN_AEHNLICHKEIT } from './statement.service';
import { environment } from '../../environments/environment';

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

  it('fragt nur gepflegte, hinreichend aehnliche Aussagen ab', () => {
    let ergebnis: unknown;
    service.aussageVorschlaege('Wärmepumpen teuer').subscribe((vorschlaege) => (ergebnis = vorschlaege));

    const anfrage = httpMock.expectOne(`${environment.baseUrl}/api/v1/statement/searchStatements`);
    expect(anfrage.request.body).toEqual({
      query_text: 'Wärmepumpen teuer',
      limit: VORSCHLAG_ANZAHL,
      nur_kuratiert: true,
      min_similarity: VORSCHLAG_MIN_AEHNLICHKEIT,
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
});
