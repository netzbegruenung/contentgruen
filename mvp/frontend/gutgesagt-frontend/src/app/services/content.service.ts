import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { tap, catchError, map } from 'rxjs/operators';
import { LoggingService } from './logging.service';
import { throwError } from 'rxjs';

export interface RecentContentResponse {
  results_count: number;
  results: any[];
}

@Injectable({
  providedIn: 'root'
})
export class ContentService {
  private baseUrl = `${environment.baseUrl}/api/v1/content`;

  constructor(
    private http: HttpClient,
    private logger: LoggingService
  ) { }

  getRecentContent(limit: number = 6): Observable<RecentContentResponse> {
    const timestamp = new Date().toISOString();
    const cacheBuster = Date.now(); // Add cache buster
    const url = `${this.baseUrl}/recent`;

    this.logger.debug('=== CONTENT SERVICE: getRecentContent START ===');
    this.logger.debug(`[${timestamp}] Making HTTP GET request to: ${url}`);
    this.logger.debug(`Query params: limit=${limit}, _t=${cacheBuster}`);
    this.logger.debug('Full URL:', `${url}?limit=${limit}&_t=${cacheBuster}`);

    // Add no-cache headers to prevent browser caching
    const headers = new HttpHeaders({
      'Cache-Control': 'no-cache, no-store, must-revalidate',
      'Pragma': 'no-cache',
      'Expires': '0'
    });

    return this.http.get<RecentContentResponse>(url, {
      params: {
        limit: limit.toString(),
        _t: cacheBuster.toString()  // Add timestamp to make each request unique
      },
      headers: headers,
      observe: 'response'  // Get full response to check headers
    }).pipe(
      tap(response => {
        const responseTimestamp = new Date().toISOString();
        this.logger.info('=== CONTENT SERVICE: HTTP Response Received ===');
        this.logger.info(`[${responseTimestamp}] Response status: ${response.status}`);
        this.logger.info(`Response headers:`, response.headers.keys());

        // Check if response is from cache
        const cacheControl = response.headers.get('cache-control');
        const etag = response.headers.get('etag');
        const lastModified = response.headers.get('last-modified');
        this.logger.info(`Cache-Control header: ${cacheControl || 'not set'}`);
        this.logger.info(`ETag header: ${etag || 'not set'}`);
        this.logger.info(`Last-Modified header: ${lastModified || 'not set'}`);

        const body = response.body!;
        this.logger.info(`Fetched ${body.results_count} recent content items`);
        this.logger.info('Content IDs received:', body.results.map(item => item.id));

        // Log details about the fetched content
        body.results.forEach((item, index) => {
          this.logger.debug(`Recent content ${index + 1}:`, {
            id: item.id,
            type: item.result_type,
            title: item.title || 'No title',
            created: item.created,
            author: item.original_author
          });
        });

        this.logger.debug('=== CONTENT SERVICE: getRecentContent END ===');
      }),
      // Extract body from response
      map(response => response.body!),
      catchError((error: any) => {
        const errorTimestamp = new Date().toISOString();
        this.logger.error(`[${errorTimestamp}] Failed to fetch recent content`, error);

        // Log error details if it's an HttpErrorResponse
        if (error instanceof HttpErrorResponse) {
          const httpErrorDetails: any = {
            message: error.message,
            status: error.status,
            statusText: error.statusText,
            url: error.url
          };
          this.logger.error('HTTP Error details:', httpErrorDetails);
        } else {
          const errorDetails: any = {
            message: error.message || 'Unknown error',
            type: error.constructor?.name || 'Unknown'
          };
          this.logger.error('Error details:', errorDetails);
        }

        return throwError(() => error);
      })
    );
  }
}
