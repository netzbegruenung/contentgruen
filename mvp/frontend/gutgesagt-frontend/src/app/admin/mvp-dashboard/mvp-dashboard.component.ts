import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule, registerLocaleData } from '@angular/common';
import localeDe from '@angular/common/locales/de';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MetricsService, MVPMetrics } from '../../services/metrics.service';
import { BilanzComponent } from '../bilanz/bilanz.component';
import { SuchenOhneTrefferComponent } from '../suchen-ohne-treffer/suchen-ohne-treffer.component';
import { MusterHinweiseComponent } from '../muster-hinweise/muster-hinweise.component';
import { FeedbackListeComponent } from '../feedback-liste/feedback-liste.component';
import { EinladungenComponent } from '../einladungen/einladungen.component';
import { Subscription } from 'rxjs';
import { nachladeStrom } from '../../shared/selbst-nachladen';
import { NachladeHinweisComponent } from '../../shared/components/nachlade-hinweis/nachlade-hinweis.component';

// Zahlen mit Komma ("2,5" statt "2.5", Persona-Runde 2, M9); die App setzt sonst keine Locale.
registerLocaleData(localeDe);

/** Der Trend auf Deutsch, mit den Woertern der Erklaerung daneben (M9: "Stable"). */
export function trendWort(trend: string): string {
  switch (trend) {
    case 'increasing': return 'Steigend';
    case 'decreasing': return 'Fallend';
    default: return 'Stabil';
  }
}

/** Die Kennzahlen aendern sich langsam: alle fuenf Minuten und beim Zurueckkehren auf den Reiter. */
export const KENNZAHLEN_NACHLADEN_MS = 5 * 60 * 1000;

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
    FeedbackListeComponent,
    EinladungenComponent,
    NachladeHinweisComponent
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
    // Laedt selbst nach (nachladeAnlaesse). Der Fehler bleibt im inneren Strom: Frueher
    // beendete ein einziger Fehler das Nachladen fuer immer.
    this.refreshSubscription = nachladeStrom(() => this.metricsService.getMVPDashboard(true), {
      sofort: true,
      ms: KENNZAHLEN_NACHLADEN_MS,
    }).subscribe((lauf) => {
      this.loading = false;
      if (lauf.fehler === null) {
        this.metrics = lauf.daten;
        this.error = null;
        this.lastUpdated = new Date();
      } else {
        console.error('Error loading MVP metrics:', lauf.fehler);
        this.error = 'Kennzahlen gerade nicht erreichbar';
      }
    });
  }

  ngOnDestroy() {
    if (this.refreshSubscription) {
      this.refreshSubscription.unsubscribe();
    }
  }

  readonly trendWort = trendWort;

  getTrendIcon(trend: string): string {
    switch (trend) {
      case 'increasing': return 'trending_up';
      case 'decreasing': return 'trending_down';
      default: return 'trending_flat';
    }
  }

  getTrendColor(trend: string): string {
    switch (trend) {
      // Theme-Variablen statt fester Farben, damit der Trend auch im Dunkelmodus lesbar ist (#588)
      case 'increasing': return 'var(--trend-steigt)';
      case 'decreasing': return 'var(--trend-faellt)';
      default: return 'var(--trend-gleich)';
    }
  }
}
