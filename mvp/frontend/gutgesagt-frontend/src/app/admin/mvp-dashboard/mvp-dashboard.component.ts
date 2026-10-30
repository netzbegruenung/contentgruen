import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MetricsService, MVPMetrics } from '../../services/metrics.service';
import { BilanzComponent } from '../bilanz/bilanz.component';
import { SuchenOhneTrefferComponent } from '../suchen-ohne-treffer/suchen-ohne-treffer.component';
import { MusterHinweiseComponent } from '../muster-hinweise/muster-hinweise.component';
import { FeedbackListeComponent } from '../feedback-liste/feedback-liste.component';
import { interval, Subscription } from 'rxjs';
import { startWith, switchMap } from 'rxjs/operators';

@Component({
  selector: 'app-mvp-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatTooltipModule,
    BilanzComponent,
    SuchenOhneTrefferComponent,
    MusterHinweiseComponent,
    FeedbackListeComponent
  ],
  templateUrl: './mvp-dashboard.component.html',
  styleUrls: ['./mvp-dashboard.component.css']
})
export class MvpDashboardComponent implements OnInit, OnDestroy {
  metrics: MVPMetrics | null = null;
  loading = true;
  error: string | null = null;
  lastUpdated: Date | null = null;
  private refreshSubscription?: Subscription;

  constructor(private metricsService: MetricsService) {}

  ngOnInit() {
    // Auto-refresh every 5 minutes
    this.refreshSubscription = interval(5 * 60 * 1000)
      .pipe(
        startWith(0),
        switchMap(() => this.metricsService.getMVPDashboard())
      )
      .subscribe({
        next: (data) => {
          this.metrics = data;
          this.loading = false;
          this.error = null;
          this.lastUpdated = new Date();
        },
        error: (err) => {
          this.error = 'Fehler beim Laden der Metriken';
          this.loading = false;
          console.error('Error loading MVP metrics:', err);
        }
      });
  }

  ngOnDestroy() {
    if (this.refreshSubscription) {
      this.refreshSubscription.unsubscribe();
    }
  }

  getTrendIcon(trend: string): string {
    switch (trend) {
      case 'increasing': return 'trending_up';
      case 'decreasing': return 'trending_down';
      default: return 'trending_flat';
    }
  }

  getTrendColor(trend: string): string {
    switch (trend) {
      case 'increasing': return 'green';
      case 'decreasing': return 'red';
      default: return 'orange';
    }
  }
}
