import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { convertToParamMap } from '@angular/router';

import { StatementService, VORSCHLAG_ANZAHL, VORSCHLAG_MIN_AEHNLICHKEIT } from './statement.service';
import { environment } from '../../environments/environment';

/**
 * findOrCreateStatement bedient zwei Situationen ueber denselben Endpunkt:
 * die Suche (das Statement faellt nebenbei an) und "Beitrag ergaenzen" (jemand
 * benennt ausdruecklich eine Aussage). Unterschieden werden sie allein ueber
 * `source`, und davon haengt im Backend ab, ob die suchende Person als Autorin
 * am Statement haengt. Deshalb wird hier festgenagelt, dass der Wert
 * unveraendert bis in den Request durchgereicht wird.
 */
describe('StatementService: Herkunft der angelegten Statements', () => {
  let service: StatementService;
  let httpMock: HttpTestingController;

  const searchUrl = `${environment.baseUrl}/api/v1/statement/searchStatements`;
  const addUrl = `${environment.baseUrl}/api/v1/statement/addStatement`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()]
    });
    service = TestBed.inject(StatementService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('reicht source=search_query an addStatement durch', () => {
    service.findOrCreateStatement('klimaschutz', 'search_query').subscribe();

    // Keine hinreichend aehnliche Aussage vorhanden -> es wird angelegt.
    httpMock.expectOne(searchUrl).flush({ results: [] });

    const anlegen = httpMock.expectOne(addUrl);
    expect(anlegen.request.body.source).toBe('search_query');
    anlegen.flush({ statement_was_new: true, statement_id: 'id-1', statement_text: 'klimaschutz' });
  });

  it('reicht source=manually_created an addStatement durch', () => {
    service.findOrCreateStatement('Die Gruenen sind eine Verbotspartei!', 'manually_created').subscribe();

    httpMock.expectOne(searchUrl).flush({ results: [] });

    const anlegen = httpMock.expectOne(addUrl);
    expect(anlegen.request.body.source).toBe('manually_created');
    anlegen.flush({ statement_was_new: true, statement_id: 'id-2', statement_text: 'x' });
  });

  it('behaelt source auch, wenn die Suche vorher scheitert', () => {
    service.findOrCreateStatement('klimaschutz', 'search_query').subscribe();

    httpMock.expectOne(searchUrl).error(new ProgressEvent('network error'));

    const anlegen = httpMock.expectOne(addUrl);
    expect(anlegen.request.body.source).toBe('search_query');
    anlegen.flush({ statement_was_new: true, statement_id: 'id-3', statement_text: 'klimaschutz' });
  });

  it('legt nichts an, wenn eine hinreichend aehnliche Aussage existiert', () => {
    service.findOrCreateStatement('klimaschutz', 'search_query').subscribe();

    httpMock.expectOne(searchUrl).flush({
      results: [{ id: 'vorhanden', text: 'Klimaschutz', replysuggestions_count: 3, score: 0.95 }]
    });

    httpMock.expectNone(addUrl);
  });
});

describe('StatementService: Aussage eines Beitragsformulars', () => {
  let service: StatementService;
  let httpMock: HttpTestingController;

  const searchUrl = `${environment.baseUrl}/api/v1/statement/searchStatements`;
  const addUrl = `${environment.baseUrl}/api/v1/statement/addStatement`;
  const linkUrl = `${environment.baseUrl}/api/v1/statement/addReplysuggestionToStatement`;
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

    it('nimmt ?searchQuery= als Text ohne ID und ohne Aufruf', () => {
      let ergebnis: unknown;
      service.aussageAusAdresse(convertToParamMap({ searchQuery: '  Waermepumpen  ' }))
        .subscribe((aussage) => (ergebnis = aussage));

      expect(ergebnis).toEqual({ statement_id: '', statement_text: 'Waermepumpen' });
    });
  });

  describe('alsAntwortVerknuepfen', () => {
    it('verknuepft direkt, wenn die ID bekannt ist', () => {
      let ergebnis: string | undefined;
      service.alsAntwortVerknuepfen('k-1', 'commentary', 1.0, { id: 'a-1', text: 'egal' })
        .subscribe((ok) => (ergebnis = ok));

      const verknuepfen = httpMock.expectOne(linkUrl);
      expect(verknuepfen.request.body).toEqual({
        statement_id: 'a-1', replysuggestion_id: 'k-1', content_type: 'commentary', relevance: 1.0,
      });
      verknuepfen.flush({ success: true });

      httpMock.expectNone(searchUrl);
      expect(ergebnis).toBe('verknuepft');
    });

    it('legt eine nur als Text bekannte Aussage erst jetzt an, als manually_created', () => {
      service.alsAntwortVerknuepfen('k-1', 'generic_text', 0.9, { id: '', text: 'Waermepumpen' }).subscribe();

      httpMock.expectOne(searchUrl).flush({ results: [] });
      const anlegen = httpMock.expectOne(addUrl);
      expect(anlegen.request.body.source).toBe('manually_created');
      anlegen.flush({ statement_was_new: true, statement_id: 'neu-1', statement_text: 'Waermepumpen' });

      expect(httpMock.expectOne(linkUrl).request.body.statement_id).toBe('neu-1');
    });

    it('ruft ohne Aussage nichts auf', () => {
      let ergebnis: string | undefined;
      service.alsAntwortVerknuepfen('k-1', 'commentary', 1.0, { id: '', text: '   ' })
        .subscribe((ok) => (ergebnis = ok));

      expect(ergebnis).toBe('ohne-aussage');
    });

    it('meldet fehlgeschlagen statt eines Fehlers, wenn das Verknuepfen scheitert', () => {
      let ergebnis: string | undefined;
      let fehler: unknown;
      service.alsAntwortVerknuepfen('k-1', 'commentary', 1.0, { id: 'a-1', text: '' })
        .subscribe({ next: (ok) => (ergebnis = ok), error: (e) => (fehler = e) });

      httpMock.expectOne(linkUrl).flush('kaputt', { status: 500, statusText: 'Server Error' });

      expect(ergebnis).toBe('fehlgeschlagen');
      expect(fehler).toBeUndefined();
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
