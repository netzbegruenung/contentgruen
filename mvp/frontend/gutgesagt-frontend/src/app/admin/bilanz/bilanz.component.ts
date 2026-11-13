import { Component, DestroyRef, OnDestroy, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { selbstNachladen } from '../../shared/selbst-nachladen';
import { NachladeHinweisComponent } from '../../shared/components/nachlade-hinweis/nachlade-hinweis.component';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { Subscription } from 'rxjs';
import { MetricsService } from '../../services/metrics.service';
import { BilanzResponse, BilanzWoche } from '../../services/dtos/metricsDtos';

/**
 * Bilanz (#467): die Kennzahlen aus #417 je Kalenderwoche. Bewusst ohne Zielwerte,
 * verglichen wird mit der Basislinie aus dem internen Launch.
 */
@Component({
  selector: 'app-bilanz',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatFormFieldModule, MatSelectModule, NachladeHinweisComponent],
  templateUrl: './bilanz.component.html',
  styleUrls: ['./bilanz.component.css'],
})
export class BilanzComponent implements OnInit, OnDestroy {
  // Die Basislinie (Wochen 2 bis 4 des internen Launchs) liegt bei der Bilanz
  // mindestens zwoelf Wochen zurueck; 8 Wochen reichen nur fuer den laufenden Blick.
  readonly zeitraeume = [8, 13, 26, 52];
  wochen = 8;
  daten: BilanzResponse | null = null;
  fehler = false;
  private anfrage?: Subscription;

  private readonly destroyRef = inject(DestroyRef);

  constructor(private metricsService: MetricsService) {}

  /** Laedt selbst nach, solange der Reiter sichtbar ist; still, ohne die Tabelle zu leeren. */
  ngOnInit() {
    this.laden();
    selbstNachladen(() => this.laden(true), this.destroyRef);
  }

  ngOnDestroy() {
    this.anfrage?.unsubscribe();
  }

  zeitraumWaehlen(wert: number) {
    this.wochen = wert;
    this.laden();
  }

  private laden(still = false) {
    // Nur die Antwort zum gewaehlten Zeitraum zaehlt: eine aeltere, die spaeter
    // ankommt, darf die Tabelle nicht ueberschreiben.
    this.anfrage?.unsubscribe();
    if (!still) {
      this.fehler = false;
    }
    this.anfrage = this.metricsService.getBilanz(this.wochen).subscribe({
      next: (daten) => {
        this.daten = daten;
        this.fehler = false;
      },
      error: () => {
        // Keine Tabelle eines anderen Zeitraums neben der Fehlermeldung; beim stillen
        // Nachladen ist es derselbe Zeitraum, die Tabelle bleibt stehen.
        if (!still) {
          this.daten = null;
        }
        this.fehler = true;
      },
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
