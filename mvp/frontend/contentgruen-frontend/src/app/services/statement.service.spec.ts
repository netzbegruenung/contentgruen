import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { StatementService } from './statement.service';
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
