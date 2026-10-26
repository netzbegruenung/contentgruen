import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { SessionService } from './session.service';

export interface ReportContentRequest {
  content_id: string;
  content_type: string;
  reason: string;
  description?: string;
}

export interface ReportContentResponse {
  success: boolean;
  message: string;
}

export interface ContentReport {
  id: string;
  content_id: string;
  content_type: string;
  reason: string;
  description: string | null;
  reported_by_user_id: string | null;
  reported_by_session_id: string | null;
  created: string;
  status: string;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  resolution_notes?: string | null;
}

export interface PendingReportsResponse {
  total: number;
  reports: ContentReport[];
}

export interface DeleteContentResponse {
  success: boolean;
  message: string;
}

@Injectable({
  providedIn: 'root'
})
export class ModerationService {
  private baseUrl = `${environment.baseUrl}/api/v1/moderation`;

  constructor(
    private http: HttpClient,
    private sessionService: SessionService
  ) {}

  reportContent(
    contentId: string,
    contentType: string,
    reason: string,
    description?: string
  ): Observable<ReportContentResponse> {
    const request: ReportContentRequest = {
      content_id: contentId,
      content_type: contentType,
      reason: reason,
      description: description
    };

    // Add session ID header for anonymous user tracking
    const headers = new HttpHeaders({
      'X-Session-Id': this.sessionService.getSessionId()
    });

    return this.http.post<ReportContentResponse>(
      `${this.baseUrl}/report`,
      request,
      { headers }
    );
  }

  getPendingReports(limit: number = 50, offset: number = 0): Observable<PendingReportsResponse> {
    // Backwards compatibility - calls getReports with 'pending' status
    return this.getReports('pending', limit, offset);
  }

  getReports(
    status: 'pending' | 'reviewed' | 'dismissed' | 'all' = 'pending',
    limit: number = 50,
    offset: number = 0
  ): Observable<PendingReportsResponse> {
    // Add cache-busting timestamp to prevent browser caching
    const timestamp = new Date().getTime();
    console.log(`[ModerationService] getReports called, status: ${status}, timestamp:`, timestamp);

    return this.http.get<PendingReportsResponse>(
      `${this.baseUrl}/reports?status=${status}&limit=${limit}&offset=${offset}&_t=${timestamp}`,
      {
        headers: {
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache'
        }
      }
    );
  }

  deleteContent(contentType: string, contentId: string): Observable<DeleteContentResponse> {
    return this.http.delete<DeleteContentResponse>(
      `${this.baseUrl}/content/${contentType}/${contentId}`
    );
  }

  dismissReport(reportId: string, notes?: string): Observable<any> {
    return this.http.put(
      `${this.baseUrl}/reports/${reportId}/dismiss`,
      { notes }
    );
  }
}
