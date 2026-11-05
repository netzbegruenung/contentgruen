import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  BilanzResponse,
  GetMetricsResponse,
  MusterHinweiseResponse,
  SuchenOhneTrefferResponse,
} from './dtos/metricsDtos';
import { environment } from '../../environments/environment';

export interface MVPMetrics {
  timestamp: string;
  period_days: number;
  daily_active_users: number;
  searches_per_user: number;
  content_created_this_week: number;
  usage_counter_total: number;
  usage_counter_current_week: number;
  usage_counter_previous_week: number;
  usage_counter_trend: string;
  helpful_rate: number;
  helpful_like_count: number;
  helpful_dislike_count: number;
  helpful_total_votes: number;
}

@Injectable({
  providedIn: 'root'
})
export class MetricsService {
  private baseUrl = `${environment.baseUrl}/api/v1/metrics`;

  constructor(private http: HttpClient) { }

  getMetrics(): Observable<GetMetricsResponse> {
    return this.http.get<GetMetricsResponse>(`${this.baseUrl}/getMetrics`);
  }

  getMVPDashboard(): Observable<MVPMetrics> {
    return this.http.get<MVPMetrics>(`${this.baseUrl}/mvp-dashboard`);
  }

  getBilanz(wochen: number): Observable<BilanzResponse> {
    return this.http.get<BilanzResponse>(`${this.baseUrl}/bilanz`, { params: { wochen } });
  }

  // Zeitraum: Standard des Backends; die Antwort nennt ihn.
  getSuchenOhneTreffer(): Observable<SuchenOhneTrefferResponse> {
    return this.http.get<SuchenOhneTrefferResponse>(`${this.baseUrl}/suchen-ohne-treffer`);
  }

  getMusterHinweise(): Observable<MusterHinweiseResponse> {
    return this.http.get<MusterHinweiseResponse>(`${this.baseUrl}/muster-hinweise`);
  }
}
