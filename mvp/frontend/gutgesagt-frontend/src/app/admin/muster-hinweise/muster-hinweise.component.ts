import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { selbstNachladen } from '../../shared/selbst-nachladen';
import { NachladeHinweisComponent } from '../../shared/components/nachlade-hinweis/nachlade-hinweis.component';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MetricsService } from '../../services/metrics.service';
import { MusterHinweis, MusterHinweiseResponse } from '../../services/dtos/metricsDtos';

/**
 * Muster-Hinweise (#352): Kontenpaare, die sich innerhalb von sieben Tagen gegenseitig genutzt haben.
 * Nur ein Hinweis für Admins; keine Automatik zieht Punkte ab (ADR 0004).
 */
@Component({
  selector: 'app-muster-hinweise',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, NachladeHinweisComponent],
  templateUrl: './muster-hinweise.component.html',
  styleUrls: ['./muster-hinweise.component.css'],
})
export class MusterHinweiseComponent implements OnInit {
  daten: MusterHinweiseResponse | null = null;
  fehler = false;

  private readonly destroyRef = inject(DestroyRef);

  constructor(private metricsService: MetricsService) {}

  /** Laedt selbst nach, solange der Reiter sichtbar ist; ein Fehler laesst den Stand stehen. */
  ngOnInit() {
    this.laden();
    selbstNachladen(() => this.metricsService.getMusterHinweise(true), this.destroyRef, {
      next: (daten) => this.uebernehmen(daten),
      error: () => (this.fehler = true),
    });
  }

  private laden() {
    this.metricsService.getMusterHinweise().subscribe({
      next: (daten) => this.uebernehmen(daten),
      error: () => (this.fehler = true),
    });
  }

  private uebernehmen(daten: MusterHinweiseResponse) {
    this.daten = daten;
    this.fehler = false;
  }

  /** Anzeigename mit Kennung; Admins sehen die Kennung (Glossar „Kennung“). */
  konto(kennung: string, name: string | null): string {
    return name ? `${name} (${kennung})` : kennung;
  }

  zeitraum(h: MusterHinweis): string {
    return h.erster_tag === h.letzter_tag ? h.letzter_tag : `${h.erster_tag} – ${h.letzter_tag}`;
  }
}
