import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { SearchService } from './search.service';
import { SessionService } from './session.service';
import { StateManagementService } from './state-management.service';
import { SearchResponse } from './dtos/searchDtos';
import { environment } from '../../environments/environment';

describe('SearchService', () => {
  let service: SearchService;
  let httpMock: HttpTestingController;
  let sessionService: SessionService;

  const searchUrl = `${environment.baseUrl}/api/v1/search/searchByText`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting()
      ]
    });
    service = TestBed.inject(SearchService);
    httpMock = TestBed.inject(HttpTestingController);
    sessionService = TestBed.inject(SessionService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('laesst nach einer gescheiterten Suche keine Ergebnisse der vorigen stehen', () => {
    const zustand = TestBed.inject(StateManagementService);
    zustand.setSearchResults({ statement_id: '11111111-2222-4333-8444-555555555555' } as SearchResponse);

    service.search('klima', 10).subscribe({ next: () => {}, error: () => {} });
    httpMock.expectOne(searchUrl).flush(null, { status: 500, statusText: 'Server Error' });

    expect(zustand.currentState.searchResults).toBeNull();
    expect(zustand.currentState.error).toBeTruthy();
    expect(zustand.currentState.loading).toBeFalse();
  });

  it('sendet die aktuelle Session-ID als X-Session-Id', () => {
    service.search('klima', 10).subscribe({ next: () => {}, error: () => {} });

    const req = httpMock.expectOne(searchUrl);
    expect(req.request.headers.get('X-Session-Id')).toBe(sessionService.getSessionId());
    req.flush(null, { status: 500, statusText: 'Server Error' });
  });

  // Kern der Zusammenfuehrung: frueher hielt SearchService eine eigene Kopie der
  // Session-ID, die im Konstruktor einmalig gelesen wurde. Nach dem Abmelden
  // haette sie die alte Kennung weitergesendet.
  it('nimmt eine neu vergebene Session-ID beim naechsten Request auf', () => {
    service.search('erste', 10).subscribe({ next: () => {}, error: () => {} });
    const first = httpMock.expectOne(searchUrl);
    const before = first.request.headers.get('X-Session-Id');
    first.flush(null, { status: 500, statusText: 'Server Error' });

    const regenerated = sessionService.regenerateSessionId();

    service.search('zweite', 10).subscribe({ next: () => {}, error: () => {} });
    const second = httpMock.expectOne(searchUrl);
    const after = second.request.headers.get('X-Session-Id');
    second.flush(null, { status: 500, statusText: 'Server Error' });

    expect(after).toBe(regenerated);
    expect(after).not.toBe(before);
  });
});
