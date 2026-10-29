import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { MeldegrundWert } from '../shared/meldegruende';
import { SperrgrundWert } from '../shared/sperrgruende';

export interface ReportContentRequest {
  content_id: string;
  content_type: string;
  reason: MeldegrundWert;
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
  // Der gemeldete Beitrag, wie die Moderation ihn liest -- auch gesperrt.
  // null, wenn er nicht mehr existiert.
  content?: GemeldeterBeitrag | null;
}

export interface GemeldeterBeitrag {
  status?: string;
  /** Nur in GET /moderation/gesperrt: die aktive Sperre; null bei Sperren vor #448. */
  sperre?: SperreFuerAdmins | null;
  [feld: string]: any;
}

/** Ergebnis der erneuten Prüfung nach einem Widerspruch. */
export type Pruefergebnis = 'sperre_bleibt' | 'entsperrt';

/** Eine Sperre, wie die Moderation sie sieht (#448). */
export interface SperreFuerAdmins {
  id: string;
  sperrgrund: string;
  begruendung: string;
  gesperrt_am: string | null;
  /** Ohne Autor sieht niemand die Sperrnachricht. */
  ohne_kontaktdaten: boolean;
  widerspruch: string | null;
  widerspruch_am: string | null;
  widerspruch_offen: boolean;
  pruefergebnis: Pruefergebnis | null;
  pruefung_begruendung: string | null;
  geprueft_am: string | null;
}

export interface PendingReportsResponse {
  total: number;
  reports: ContentReport[];
}

export interface SperreResponse {
  success: boolean;
  message: string;
}

/** Gesperrte Beiträge, auch ohne Meldung (GET /moderation/gesperrt). */
export interface GesperrteResponse {
  total: number;
  beitraege: GemeldeterBeitrag[];
}

@Injectable({
  providedIn: 'root'
})
export class ModerationService {
  private baseUrl = `${environment.baseUrl}/api/v1/moderation`;

  constructor(
    private http: HttpClient
  ) {}

  reportContent(
    contentId: string,
    contentType: string,
    reason: MeldegrundWert,
    description?: string
  ): Observable<ReportContentResponse> {
    const request: ReportContentRequest = {
      content_id: contentId,
      content_type: contentType,
      reason: reason,
      description: description
    };

    return this.http.post<ReportContentResponse>(`${this.baseUrl}/report`, request);
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

  /** Sperren verlangt Sperrgrund und Begründung; beides erfährt der Autor (#448). */
  sperren(contentId: string, sperrgrund: SperrgrundWert, begruendung: string): Observable<SperreResponse> {
    return this.http.put<SperreResponse>(`${this.baseUrl}/content/${contentId}/sperren`, {
      sperrgrund,
      begruendung,
    });
  }

  /** Nach einem Widerspruch erneut geprüft: Die Sperre bleibt. */
  sperreBestaetigen(sperreId: string, begruendung: string): Observable<SperreResponse> {
    return this.http.put<SperreResponse>(`${this.baseUrl}/sperren/${sperreId}/bestaetigen`, {
      begruendung,
    });
  }

  entsperren(contentId: string): Observable<SperreResponse> {
    return this.http.put<SperreResponse>(`${this.baseUrl}/content/${contentId}/entsperren`, {});
  }

  getGesperrte(): Observable<GesperrteResponse> {
    return this.http.get<GesperrteResponse>(`${this.baseUrl}/gesperrt`);
  }

  dismissReport(reportId: string, notes?: string): Observable<any> {
    return this.http.put(
      `${this.baseUrl}/reports/${reportId}/dismiss`,
      { notes }
    );
  }
}
