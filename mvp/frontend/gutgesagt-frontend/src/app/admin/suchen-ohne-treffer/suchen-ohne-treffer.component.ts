import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MetricsService } from '../../services/metrics.service';
import { SuchenOhneTrefferResponse } from '../../services/dtos/metricsDtos';

/**
 * Kennzahl "Suchen ohne Treffer": die haeufigsten Suchanfragen der letzten Wochen,
 * zu denen die Suche keinen Beitrag fand. Zeigt den Text der Aussage, auf der sie
 * gelandet sind, und die Anzahl, nichts ueber die Suchenden.
 */
@Component({
  selector: 'app-suchen-ohne-treffer',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule],
  templateUrl: './suchen-ohne-treffer.component.html',
  styleUrls: ['./suchen-ohne-treffer.component.css'],
})
export class SuchenOhneTrefferComponent implements OnInit {
  daten: SuchenOhneTrefferResponse | null = null;
  fehler = false;

  constructor(private metricsService: MetricsService) {}

  ngOnInit() {
    this.metricsService.getSuchenOhneTreffer().subscribe({
      next: (daten) => (this.daten = daten),
      error: () => (this.fehler = true),
    });
  }
}
