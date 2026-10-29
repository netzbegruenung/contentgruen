import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MetricsService } from '../../services/metrics.service';
import { BilanzResponse, BilanzWoche } from '../../services/dtos/metricsDtos';

/**
 * Bilanz (#467): die Kennzahlen aus #417 je Kalenderwoche. Bewusst ohne Zielwerte,
 * verglichen wird mit der Basislinie aus dem internen Launch.
 */
@Component({
  selector: 'app-bilanz',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule],
  templateUrl: './bilanz.component.html',
  styleUrls: ['./bilanz.component.css'],
})
export class BilanzComponent implements OnInit {
  daten: BilanzResponse | null = null;
  fehler = false;

  constructor(private metricsService: MetricsService) {}

  ngOnInit() {
    this.metricsService.getBilanz().subscribe({
      next: (daten) => (this.daten = daten),
      error: () => (this.fehler = true),
    });
  }

  woche(w: BilanzWoche): string {
    // Als UTC lesen: woche_ab ist ein Datum ohne Uhrzeit.
    const montag = new Date(`${w.woche_ab}T00:00:00Z`).toLocaleDateString('de-DE', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      timeZone: 'UTC',
    });
    return w.tage < 7 ? `ab ${montag} (laufend, ${w.tage} Tage)` : `ab ${montag}`;
  }

  zahl(wert: number | null, einheit = ''): string {
    return wert === null ? '–' : `${wert.toLocaleString('de-DE', { maximumFractionDigits: 2 })}${einheit}`;
  }
}
