import { Component, OnInit } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MetricsService } from '../services/metrics.service';
import { GetMetricsResponse } from '../services/dtos/metricsDtos';
import { CommonModule } from '@angular/common';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatExpansionModule } from '@angular/material/expansion';

@Component({
  selector: 'app-metrics',
  standalone: true,
  imports: [
    MatCardModule,
    CommonModule,
    MatTooltipModule,
    MatExpansionModule
  ],
  templateUrl: './metrics.component.html',
  styleUrls: ['./metrics.component.css']
})
export class MetricsComponent implements OnInit {
  metrics: GetMetricsResponse | null = null;  // This will hold the metrics data
  isExpanded: boolean = false;  // Control panel expansion
  isFirstVisit: boolean = false;  // Track if this is the user's first visit

  constructor(private metricsService: MetricsService) { }

  // This will trigger when the component loads
  ngOnInit(): void {
    this.checkFirstVisit();
    this.loadMetrics();
  }

  private checkFirstVisit(): void {
    const hasVisited = localStorage.getItem('gutgesagt-metrics-seen');
    if (!hasVisited) {
      this.isFirstVisit = true;
      this.isExpanded = true; // Auto-expand for first-time visitors
      // Mark as seen after a short delay to ensure they see it
      setTimeout(() => {
        localStorage.setItem('gutgesagt-metrics-seen', 'true');
      }, 3000);
    }
  }

  loadMetrics(): void {
    this.metricsService.getMetrics().subscribe({
      next: (data: GetMetricsResponse) => {
        this.metrics = data;
      },
      error: (error) => {

        this.metrics = {
          content_count: -1,
          content_count_last_week: -1,
          statement_count: -1,
          statement_count_last_week: -1,
          commentary_count: -1,
          commentary_count_last_week: -1,
          reference_count: -1,
          reference_count_last_week: -1,
          requested_commentary_count: -1,
          active_users_count: -1
        }
      }
    });
  }
}
