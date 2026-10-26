import { TestBed, ComponentFixture, fakeAsync, tick } from '@angular/core/testing';
import { Router } from '@angular/router';
import { Location } from '@angular/common';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { provideAnimations } from '@angular/platform-browser/animations';
import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { routes } from '../app.routes';
import { AuthInterceptor } from '../auth/auth.interceptor';
import { environment } from '../../environments/environment';
import { SearchResponse } from '../services/dtos/searchDtos';
import { ContentStatus } from '../services/dtos/content-status-enum';
import { ContentOrigin } from '../services/dtos/content-origin-enum';
import { ContentVisibility } from '../services/dtos/content-visibility-enum';

@Component({
  selector: 'app-test-root',
  template: '<router-outlet></router-outlet>',
  standalone: true,
  imports: [RouterOutlet]
})
class TestRootComponent {}

xdescribe('Anonymous Search Flow Integration', () => {  // TODO: Re-enable when setting up comprehensive integration test suite
  let router: Router;
  let location: Location;
  let httpMock: HttpTestingController;
  let fixture: ComponentFixture<TestRootComponent>;

  const mockSearchResponse: SearchResponse = {
    query_was_newly_added_as_statement: false,
    statement_id: 'stmt-123',
    statement_text: 'renewable energy',
    commentary_search_results_count: 1,
    commentary_search_results: [
      {
        score: 0.95,
        statement_text: 'renewable energy',
        statement_similarity_score: 0.9,
        reply_relevance: 0.85,
        commentary_result: {
          id: '123',
          text: 'Test commentary about renewable energy',
          content_type: 'commentary',
          status: ContentStatus.APPROVED,
          origin: ContentOrigin.MANUALLY_CREATED,
          original_author: 'Author',
          created: new Date().toISOString(),
          last_modified: new Date().toISOString(),
          last_modified_by: 'Author',
          authors: [],
          edit_history: [],
          most_similar_similarity_score: 0,
          most_similar_content_id: '',
          visibility: ContentVisibility.VISIBLE,
          references: [],
          report_count: 0,
          is_archived: false,
          report_flagged: false,
          rejection_reason: '',
          block_reason: '',
          title: 'Test Title',
          long_text: 'Test commentary about renewable energy - extended version',
          short_text: 'Test commentary',
          references_count: 0,
          score: 0.95
        }
      }
    ],
    generictext_search_results_count: 0,
    generictext_search_results: []
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TestRootComponent],
      providers: [
        provideHttpClient(withInterceptors([AuthInterceptor])),
        provideHttpClientTesting(),
        provideRouter(routes),
        provideAnimations()
      ]
    }).compileComponents();

    router = TestBed.inject(Router);
    location = TestBed.inject(Location);
    httpMock = TestBed.inject(HttpTestingController);

    fixture = TestBed.createComponent(TestRootComponent);
    fixture.detectChanges();
  });

  afterEach(() => {
    httpMock.verify();
  });

  describe('Anonymous User Access', () => {
    it('should allow anonymous users to access search page', fakeAsync(() => {
      // Navigate to search
      router.navigate(['/search']);
      tick();

      // PublicGuard should check session but allow access regardless
      const sessionReq = httpMock.expectOne(`${environment.baseUrl}/api/check-session`);
      sessionReq.flush(null, { status: 401, statusText: 'Unauthorized' });
      tick();

      // Should be on search page, not redirected
      expect(location.path()).toBe('/search');
    }));

    it('should allow anonymous users to access result page', fakeAsync(() => {
      // Navigate to results with search query
      router.navigate(['/result'], { queryParams: { searchQuery: 'test' } });
      tick();

      // PublicGuard should check session but allow access
      const sessionReq = httpMock.expectOne(`${environment.baseUrl}/api/check-session`);
      sessionReq.flush(null, { status: 401, statusText: 'Unauthorized' });
      tick();

      // Should be on result page
      expect(location.path()).toBe('/result?searchQuery=test');
    }));

    it('should perform search without authentication', fakeAsync(() => {
      // Navigate to result page with query
      router.navigate(['/result'], { queryParams: { searchQuery: 'climate' } });
      tick();

      // Handle session check
      const sessionReq = httpMock.expectOne(`${environment.baseUrl}/api/check-session`);
      sessionReq.flush(null, { status: 401, statusText: 'Unauthorized' });
      tick();

      // Search request should be made
      const searchReq = httpMock.expectOne(`${environment.baseUrl}/api/v1/search/searchByText`);
      expect(searchReq.request.body).toEqual({
        query_text: 'climate',
        limit: 10
      });
      expect(searchReq.request.withCredentials).toBe(true);

      // Return mock search results
      searchReq.flush(mockSearchResponse);
      tick();

      // Should still be on result page
      expect(location.path()).toBe('/result?searchQuery=climate');
    }));

    it('should handle 401 on search endpoint without redirecting', fakeAsync(() => {
      // Navigate to result page
      router.navigate(['/result'], { queryParams: { searchQuery: 'test' } });
      tick();

      // Handle session check
      const sessionReq = httpMock.expectOne(`${environment.baseUrl}/api/check-session`);
      sessionReq.flush(null, { status: 401, statusText: 'Unauthorized' });
      tick();

      // Search request returns 401
      const searchReq = httpMock.expectOne(`${environment.baseUrl}/api/v1/search/searchByText`);
      searchReq.flush(null, { status: 401, statusText: 'Unauthorized' });
      tick();

      // Should NOT redirect to login
      expect(location.path()).toBe('/result?searchQuery=test');
    }));
  });

  describe('Protected Routes', () => {
    it('should redirect anonymous users from contribute page', fakeAsync(() => {
      // Try to navigate to contribute
      router.navigate(['/contribute']);
      tick();

      // AuthGuard should check session
      const sessionReq = httpMock.expectOne(`${environment.baseUrl}/api/check-session`);
      sessionReq.flush(null, { status: 401, statusText: 'Unauthorized' });
      tick();

      // Should redirect to login with returnUrl
      expect(location.path()).toBe('/login?returnUrl=%2Fcontribute');
    }));

    it('should redirect anonymous users from contributions page', fakeAsync(() => {
      // Try to navigate to contributions
      router.navigate(['/contributions']);
      tick();

      // AuthGuard should check session
      const sessionReq = httpMock.expectOne(`${environment.baseUrl}/api/check-session`);
      sessionReq.flush(null, { status: 401, statusText: 'Unauthorized' });
      tick();

      // Should redirect to login with returnUrl
      expect(location.path()).toBe('/login?returnUrl=%2Fcontributions');
    }));

    it('should allow authenticated users to access contribute page', fakeAsync(() => {
      // Navigate to contribute
      router.navigate(['/contribute']);
      tick();

      // AuthGuard checks session - user is authenticated
      const sessionReq = httpMock.expectOne(`${environment.baseUrl}/api/check-session`);
      sessionReq.flush({ authenticated: true });
      tick();

      // Should be on contribute page
      expect(location.path()).toBe('/contribute');
    }));
  });

  describe('Search Flow End-to-End', () => {
    it('should complete full anonymous search flow', fakeAsync(() => {
      // 1. Start at search page
      router.navigate(['/search']);
      tick();

      const sessionReq1 = httpMock.expectOne(`${environment.baseUrl}/api/check-session`);
      sessionReq1.flush(null, { status: 401, statusText: 'Unauthorized' });
      tick();

      expect(location.path()).toBe('/search');

      // 2. Navigate to results with search query
      router.navigate(['/result'], { queryParams: { searchQuery: 'renewable energy' } });
      tick();

      const sessionReq2 = httpMock.expectOne(`${environment.baseUrl}/api/check-session`);
      sessionReq2.flush(null, { status: 401, statusText: 'Unauthorized' });
      tick();

      // 3. Perform search
      const searchReq = httpMock.expectOne(`${environment.baseUrl}/api/v1/search/searchByText`);
      expect(searchReq.request.body.query_text).toBe('renewable energy');
      searchReq.flush(mockSearchResponse);
      tick();

      // 4. Should display results without requiring login
      expect(location.path()).toBe('/result?searchQuery=renewable%20energy');
    }));

    it('should handle navigation from results back to search', fakeAsync(() => {
      // Start at results
      router.navigate(['/result'], { queryParams: { searchQuery: 'test' } });
      tick();

      const sessionReq1 = httpMock.expectOne(`${environment.baseUrl}/api/check-session`);
      sessionReq1.flush(null, { status: 401, statusText: 'Unauthorized' });
      tick();

      const searchReq = httpMock.expectOne(`${environment.baseUrl}/api/v1/search/searchByText`);
      searchReq.flush(mockSearchResponse);
      tick();

      // Navigate back to search
      router.navigate(['/search']);
      tick();

      const sessionReq2 = httpMock.expectOne(`${environment.baseUrl}/api/check-session`);
      sessionReq2.flush(null, { status: 401, statusText: 'Unauthorized' });
      tick();

      // Should be on search page
      expect(location.path()).toBe('/search');
    }));
  });

  describe('Mixed Authentication States', () => {
    it('should handle user login during session', fakeAsync(() => {
      // Start as anonymous on search
      router.navigate(['/search']);
      tick();

      const sessionReq1 = httpMock.expectOne(`${environment.baseUrl}/api/check-session`);
      sessionReq1.flush(null, { status: 401, statusText: 'Unauthorized' });
      tick();

      // Perform search as anonymous
      router.navigate(['/result'], { queryParams: { searchQuery: 'test' } });
      tick();

      const sessionReq2 = httpMock.expectOne(`${environment.baseUrl}/api/check-session`);
      sessionReq2.flush(null, { status: 401, statusText: 'Unauthorized' });
      tick();

      const searchReq = httpMock.expectOne(`${environment.baseUrl}/api/v1/search/searchByText`);
      searchReq.flush(mockSearchResponse);
      tick();

      // Now navigate to contribute (requires auth)
      router.navigate(['/contribute']);
      tick();

      // This time user is authenticated
      const sessionReq3 = httpMock.expectOne(`${environment.baseUrl}/api/check-session`);
      sessionReq3.flush({ authenticated: true });
      tick();

      // Should be on contribute page
      expect(location.path()).toBe('/contribute');
    }));
  });
});
