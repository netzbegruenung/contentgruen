import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { SearchService } from './search.service';
import { StateManagementService } from './state-management.service';
import { SearchResponse } from './dtos/searchDtos';
import { environment } from '../../environments/environment';

describe('SearchService', () => {
  let service: SearchService;
  let httpMock: HttpTestingController;

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

  it('sendet keine Kennung des Browsers mit (#446)', () => {
    service.search('klima', 10).subscribe({ next: () => {}, error: () => {} });

    const req = httpMock.expectOne(searchUrl);
    expect(req.request.headers.has('X-Session-Id')).toBeFalse();
    req.flush(null, { status: 500, statusText: 'Server Error' });
  });
});
