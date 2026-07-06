import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { tap, catchError } from 'rxjs/operators';
import { SearchByTextRequest, SearchResponse } from './dtos/searchDtos';
import { environment } from '../../environments/environment';
import { LoggingService } from './logging.service';
import { StateManagementService } from './state-management.service';
import { throwError } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class SearchService {
  private searchApiUrl = `${environment.baseUrl}/api/v1/search/searchByText`;
  private sessionId: string;

  constructor(
    private http: HttpClient,
    private logger: LoggingService,
    private stateService: StateManagementService
  ) {
    // Get or create session ID for tracking
    this.sessionId = this.getOrCreateSessionId();
  }

  private getOrCreateSessionId(): string {
    const storageKey = 'contentgruen_session_id';
    let sessionId = localStorage.getItem(storageKey);

    if (!sessionId) {
      sessionId = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
      });
      localStorage.setItem(storageKey, sessionId);
    }

    return sessionId;
  }

  search(queryText: string, limit: number): Observable<SearchResponse> {
    this.logger.debug('Searching for:', queryText);

    // Update state
    this.stateService.setSearchQuery(queryText);
    this.stateService.setLoading(true);

    const requestPayload: SearchByTextRequest = {
      query_text: queryText,
      limit: limit
    };

    // Add session ID header for metrics tracking
    const headers = new HttpHeaders({
      'X-Session-Id': this.sessionId
    });

    return this.http.post<SearchResponse>(this.searchApiUrl, requestPayload, { headers }).pipe(
      tap(response => {
        this.stateService.setSearchResults(response);

        const totalResults = response.commentary_search_results_count + response.generictext_search_results_count;

        // Log detailed search results
        this.logger.info(`Search completed successfully - Found ${totalResults} results`);
        this.logger.info('Query resulted in:', {
          new_statement: response.query_was_newly_added_as_statement,
          statement_id: response.statement_id,
          statement_text: response.statement_text
        });

        // Log commentary results
        if (response.commentary_search_results_count > 0) {
          this.logger.debug(`Found ${response.commentary_search_results_count} commentary results:`);
          response.commentary_search_results.forEach((item, index) => {
            this.logger.debug(`Commentary ${index + 1}:`, {
              id: item.commentary_result.id,
              title: item.commentary_result.title,
              style: item.commentary_result.style,
              text: item.commentary_result.text.substring(0, 100) + '...',
              score: item.score,
              statement_similarity: item.statement_similarity_score,
              reply_relevance: item.reply_relevance,
              status: item.commentary_result.status,
              origin: item.commentary_result.origin,
              author: item.commentary_result.original_author,
              references: item.commentary_result.references?.length || 0
            });
          });
        }

        // Log generictext results
        if (response.generictext_search_results_count > 0) {
          this.logger.debug(`Found ${response.generictext_search_results_count} generic text results:`);
          response.generictext_search_results.forEach((item, index) => {
            this.logger.debug(`Generic Text ${index + 1}:`, {
              id: item.generictext_result.id,
              title: item.generictext_result.title,
              text: item.generictext_result.text.substring(0, 100) + '...',
              score: item.score,
              statement_similarity: item.statement_similarity_score,
              reply_relevance: item.reply_relevance,
              status: item.generictext_result.status,
              origin: item.generictext_result.origin,
              author: item.generictext_result.original_author
            });
          });
        }

        // Log summary
        this.logger.info('Search results summary:', {
          total: totalResults,
          commentaries: response.commentary_search_results_count,
          generic_texts: response.generictext_search_results_count,
          query: queryText
        });
      }),
      catchError(error => {
        const errorMessage = error.message || 'Fehler bei der Suche';
        this.stateService.setError(errorMessage);
        this.logger.error('Search failed', error);
        return throwError(() => error);
      })
    );
  }
}
