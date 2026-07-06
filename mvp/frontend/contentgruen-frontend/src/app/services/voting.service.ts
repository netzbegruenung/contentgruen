import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';
import { environment } from '../../environments/environment';
import { LoggingService } from './logging.service';

export interface VoteRequest {
  content_id: string;
  vote_type: 'like' | 'dislike';
}

export interface VoteResponse {
  content_id: string;
  vote_type: string | null;
  message: string;
}

export interface VoteStats {
  content_id: string;
  likes: number;
  dislikes: number;
  score: number;
}

@Injectable({
  providedIn: 'root'
})
export class VotingService {
  private apiUrl = `${environment.baseUrl}/api/v1/voting`;

  constructor(
    private http: HttpClient,
    private loggingService: LoggingService
  ) {}

  /**
   * Set a like for a content item (idempotent)
   */
  setLike(contentId: string): Observable<VoteResponse> {
    this.loggingService.logInteraction('vote_like', { contentId });

    return this.http.put<VoteResponse>(`${this.apiUrl}/content/${contentId}/like`, {}).pipe(
      tap(response => {
        this.loggingService.logInteraction('like_set', {
          contentId,
          message: response.message
        });
      }),
      catchError(error => {
        this.loggingService.logError('Failed to set like', error);
        return throwError(() => error);
      })
    );
  }

  /**
   * Remove a like for a content item (idempotent)
   */
  removeLike(contentId: string): Observable<VoteResponse> {
    this.loggingService.logInteraction('remove_like', { contentId });

    return this.http.delete<VoteResponse>(`${this.apiUrl}/content/${contentId}/like`).pipe(
      tap(response => {
        this.loggingService.logInteraction('like_removed', {
          contentId,
          message: response.message
        });
      }),
      catchError(error => {
        this.loggingService.logError('Failed to remove like', error);
        return throwError(() => error);
      })
    );
  }

  /**
   * Set a dislike for a content item (idempotent)
   */
  setDislike(contentId: string): Observable<VoteResponse> {
    this.loggingService.logInteraction('vote_dislike', { contentId });

    return this.http.put<VoteResponse>(`${this.apiUrl}/content/${contentId}/dislike`, {}).pipe(
      tap(response => {
        this.loggingService.logInteraction('dislike_set', {
          contentId,
          message: response.message
        });
      }),
      catchError(error => {
        this.loggingService.logError('Failed to set dislike', error);
        return throwError(() => error);
      })
    );
  }

  /**
   * Remove a dislike for a content item (idempotent)
   */
  removeDislike(contentId: string): Observable<VoteResponse> {
    this.loggingService.logInteraction('remove_dislike', { contentId });

    return this.http.delete<VoteResponse>(`${this.apiUrl}/content/${contentId}/dislike`).pipe(
      tap(response => {
        this.loggingService.logInteraction('dislike_removed', {
          contentId,
          message: response.message
        });
      }),
      catchError(error => {
        this.loggingService.logError('Failed to remove dislike', error);
        return throwError(() => error);
      })
    );
  }

  /**
   * Get the current user's vote for a specific content item
   */
  getUserVote(contentId: string): Observable<{ content_id: string; vote_type: string | null }> {
    return this.http.get<{ content_id: string; vote_type: string | null }>(
      `${this.apiUrl}/content/${contentId}`
    ).pipe(
      catchError(error => {
        this.loggingService.logError('Failed to get user vote', error);
        return throwError(() => error);
      })
    );
  }

  /**
   * Get the current user's votes for multiple content items
   */
  getUserVotesBatch(contentIds: string[]): Observable<{ [key: string]: string }> {
    return this.http.post<{ [key: string]: string }>(
      `${this.apiUrl}/votes/batch`,
      contentIds
    ).pipe(
      catchError(error => {
        this.loggingService.logError('Failed to get user votes batch', error);
        return throwError(() => error);
      })
    );
  }

  /**
   * Get voting statistics for a content item (likes, dislikes, score)
   */
  getVoteStats(contentId: string): Observable<VoteStats> {
    return this.http.get<VoteStats>(`${this.apiUrl}/content/${contentId}/stats`).pipe(
      catchError(error => {
        this.loggingService.logError('Failed to get vote stats', error);
        return throwError(() => error);
      })
    );
  }

  // Legacy method - kept for backward compatibility
  // Use removeLike() or removeDislike() instead
}
