import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { GetMetricsResponse } from './dtos/metricsDtos';
import { environment } from '../../environments/environment';

export interface MVPMetrics {
  timestamp: string;
  period_days: number;
  daily_active_users: number;
  daily_active_users_goal: number;
  daily_active_users_met: boolean;
  searches_per_user: number;
  searches_per_user_goal: number;
  searches_per_user_met: boolean;
  content_created_this_week: number;
  content_created_goal: number;
  content_created_met: boolean;
  usage_counter_total: number;
  usage_counter_current_week: number;
  usage_counter_previous_week: number;
  usage_counter_trend: string;
  usage_counter_met: boolean;
  helpful_rate: number;
  helpful_rate_goal: number;
  helpful_rate_met: boolean;
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
}
