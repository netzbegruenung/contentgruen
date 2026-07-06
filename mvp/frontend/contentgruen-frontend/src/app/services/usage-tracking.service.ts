import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, of, Subject } from 'rxjs';
import { catchError, tap, debounceTime, distinctUntilChanged } from 'rxjs/operators';
import { environment } from '../../environments/environment';
import { LoggingService } from './logging.service';
import { SessionService } from './session.service';

export interface TrackUsageRequest {
  session_id?: string;
}

export interface TrackUsageResponse {
  success: boolean;
  message: string;
  usage_count: number;
}

export interface ContentUsageStats {
  usage_count: number;
}

export interface UserUsageStats {
  user_id: string;
  unique_contents_contributed: number;
  total_usage_count: number;
  top_content: Array<{
    content_id: string;
    usage_count: number;
  }>;
}

export interface TrendingContent {
  trending: Array<{
    content_id: string;
    recent_uses: number;
    total_uses: number;
  }>;
}

@Injectable({
  providedIn: 'root'
})
export class UsageTrackingService {
  private apiUrl = `${environment.baseUrl}/api/v1/usage`;

  // Debouncing mechanism for rapid copy events
  private copyEventSubject = new Subject<string>();
  private recentCopies = new Map<string, number>(); // Track recent copies with timestamps

  constructor(
    private http: HttpClient,
    private loggingService: LoggingService,
    private sessionService: SessionService
  ) {
    // Set up debounced copy event handler
    this.setupDebouncedCopyHandler();
  }

  private setupDebouncedCopyHandler(): void {
    // Process copy events with debouncing
    // Wait 500ms after the last event before processing
    this.copyEventSubject.pipe(
      debounceTime(500),
      distinctUntilChanged()
    ).subscribe(contentId => {
      this.performUsageTracking(contentId);
    });
  }


  /**
   * Track that a content item was used (copied).
   * Uses debouncing to prevent rapid duplicate tracking.
   *
   * @param contentId - The ID of the content item
   * @returns Observable that completes immediately (fire-and-forget)
   */
  trackContentUsage(contentId: string): Observable<any> {
    // Check if this content was recently copied (within 2 seconds)
    const now = Date.now();
    const lastCopyTime = this.recentCopies.get(contentId);

    if (lastCopyTime && (now - lastCopyTime) < 2000) {
      // Skip duplicate copy within 2 seconds
      this.loggingService.debug(`Skipping duplicate copy tracking for ${contentId}`);
      return of({ tracked: false, reason: 'duplicate' });
    }

    // Update the last copy time
    this.recentCopies.set(contentId, now);

    // Clean up old entries (older than 5 seconds)
    this.cleanupRecentCopies();

    // Emit to the debounced subject
    this.copyEventSubject.next(contentId);

    // Return immediately without waiting
    return of({ tracked: true, queued: true });
  }

  /**
   * Perform the actual usage tracking (called after debouncing).
   * @private
   */
  private performUsageTracking(contentId: string): void {
    const url = `${this.apiUrl}/content/${contentId}/usage`;
    const body: TrackUsageRequest = {
      session_id: this.sessionService.getSessionId()
    };

    // Fire the request but don't wait for response
    // Using catchError to handle failures silently
    this.http.post<TrackUsageResponse>(url, body)
      .pipe(
        tap(response => {
          if (response?.success) {
            this.loggingService.info(`Usage tracked for content ${contentId}: ${response.usage_count} uses`);
          }
        }),
        catchError(error => {
          // Log error but don't propagate it (fire-and-forget)
          this.loggingService.error(`Failed to track usage for content ${contentId}`, error);
          return of(null);
        })
      )
      .subscribe(); // Execute the request
  }

  /**
   * Clean up old entries from recent copies map to prevent memory leak.
   * @private
   */
  private cleanupRecentCopies(): void {
    const now = Date.now();
    const cutoff = now - 5000; // 5 seconds

    for (const [contentId, timestamp] of this.recentCopies.entries()) {
      if (timestamp < cutoff) {
        this.recentCopies.delete(contentId);
      }
    }
  }

  /**
   * Get the usage count for a specific content item.
   *
   * @param contentId - The ID of the content item
   * @returns Observable with usage count
   */
  getContentUsage(contentId: string): Observable<ContentUsageStats> {
    const url = `${this.apiUrl}/content/${contentId}/usage`;

    return this.http.get<ContentUsageStats>(url)
      .pipe(
        catchError(error => {
          this.loggingService.error(`Failed to get usage for content ${contentId}`, error);
          return of({ usage_count: 0 });
        })
      );
  }

  /**
   * Get usage statistics for a specific user's contributed content.
   *
   * @param userId - The ID of the user
   * @returns Observable with user statistics
   */
  getUserUsageStats(userId: string): Observable<UserUsageStats> {
    const url = `${this.apiUrl}/users/${userId}/usage-stats`;

    return this.http.get<UserUsageStats>(url)
      .pipe(
        catchError(error => {
          this.loggingService.error(`Failed to get usage stats for user ${userId}`, error);
          return of({
            user_id: userId,
            unique_contents_contributed: 0,
            total_usage_count: 0,
            top_content: []
          });
        })
      );
  }

  /**
   * Get currently trending content based on recent usage.
   *
   * @param limit - Maximum number of items to return (default: 10)
   * @returns Observable with trending content
   */
  getTrendingContent(limit: number = 10): Observable<TrendingContent> {
    const url = `${this.apiUrl}/trending?limit=${limit}`;

    return this.http.get<TrendingContent>(url)
      .pipe(
        catchError(error => {
          this.loggingService.error('Failed to get trending content', error);
          return of({ trending: [] });
        })
      );
  }

  /**
   * Track usage with optimistic UI update.
   * Returns the optimistic count immediately while tracking in background.
   *
   * @param contentId - The ID of the content item
   * @param currentCount - The current usage count for optimistic update
   * @returns The optimistic new count
   */
  trackWithOptimisticUpdate(contentId: string, currentCount: number): number {
    // Fire tracking request in background
    this.trackContentUsage(contentId);

    // Return optimistic count immediately
    return currentCount + 1;
  }

  /**
   * Check if tracking is available (for offline detection).
   *
   * @returns True if online and tracking is available
   */
  isTrackingAvailable(): boolean {
    return navigator.onLine;
  }
}
