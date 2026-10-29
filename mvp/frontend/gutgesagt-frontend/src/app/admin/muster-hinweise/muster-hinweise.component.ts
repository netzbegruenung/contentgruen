import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MetricsService } from '../../services/metrics.service';
import { MusterHinweis, MusterHinweiseResponse } from '../../services/dtos/metricsDtos';

/**
 * Muster-Hinweise (#352): Kontenpaare, die sich am selben Tag gegenseitig genutzt haben.
 * Nur ein Hinweis für Admins; keine Automatik zieht Punkte ab (ADR 0004).
 */
@Component({
  selector: 'app-muster-hinweise',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule],
  templateUrl: './muster-hinweise.component.html',
  styleUrls: ['./muster-hinweise.component.css'],
})
export class MusterHinweiseComponent implements OnInit {
  daten: MusterHinweiseResponse | null = null;
  fehler = false;

  constructor(private metricsService: MetricsService) {}

  ngOnInit() {
    this.metricsService.getMusterHinweise().subscribe({
      next: (daten) => (this.daten = daten),
      error: () => (this.fehler = true),
    });
  }

  /** Anzeigename mit Kennung; Admins sehen die Kennung (Glossar „Kennung“). */
  konto(kennung: string, name: string | null): string {
    return name ? `${name} (${kennung})` : kennung;
  }

  zeitraum(h: MusterHinweis): string {
    return h.erster_tag === h.letzter_tag ? h.letzter_tag : `${h.erster_tag} – ${h.letzter_tag}`;
  }
}
