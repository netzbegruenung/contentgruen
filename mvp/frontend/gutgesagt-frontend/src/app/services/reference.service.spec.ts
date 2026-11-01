import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { ReferenceService } from './reference.service';
import { NUR_LESEND } from '../auth/cache.interceptor';
import { environment } from '../../environments/environment';

describe('ReferenceService', () => {
  let service: ReferenceService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(ReferenceService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  describe('searchReferences', () => {
    it('markiert die Herkunftssuche als nur lesend, damit sie den Cache stehen laesst', () => {
      service.searchReferences({ query_text: 'klimaschutz', limit: 3 }).subscribe();

      const anfrage = httpMock.expectOne(`${environment.baseUrl}/api/v1/reference/search`);
      expect(anfrage.request.method).toBe('POST');
      expect(anfrage.request.context.get(NUR_LESEND)).toBeTrue();
      anfrage.flush({ results: [] });
    });

    it('markiert das Anlegen einer Herkunft nicht: es schreibt', () => {
      service.addReference({ url: 'https://example.org/a' } as never).subscribe();

      const anfrage = httpMock.expectOne(`${environment.baseUrl}/api/v1/reference/add`);
      expect(anfrage.request.context.get(NUR_LESEND)).toBeFalse();
      anfrage.flush({});
    });
  });
});
