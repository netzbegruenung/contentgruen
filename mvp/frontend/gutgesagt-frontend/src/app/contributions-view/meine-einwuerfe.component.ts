import { ChangeDetectionStrategy, ChangeDetectorRef, Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { BreakpointObserver } from '@angular/cdk/layout';
import { MatPaginator, MatPaginatorIntl, PageEvent } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

import { EinwurfService } from '../services/einwurf.service';
import { LoggingService } from '../services/logging.service';
import { BeitragskarteComponent } from '../beitragskarte/beitragskarte.component';
import { EinwurfAktion, KartenDaten, ausEinwurf } from '../beitragskarte/karten-daten';
import { EinwurfAktionenService } from '../raw-input-list/einwurf-aktionen.service';
import { DeutscherPaginatorIntl } from '../shared/paginator-intl-de';

/**
 * Meine Einwuerfe: was aus den eigenen Funden geworden ist.
 *
 * Jede Stufe, auch verworfen, neueste zuerst; die Stufe steht als Wort auf der
 * Karte. Bei ausformulierten fuehrt "Ansehen" zu den verknuepften Beitraegen. Die
 * Karte ist dieselbe wie im Fangkorb und bietet dieselben Griffe - wer hier sieht,
 * dass ein Einwurf noch offen ist, kann ihn gleich selbst destillieren.
 */
@Component({
  selector: 'app-meine-einwuerfe',
  standalone: true,
  imports: [CommonModule, MatPaginator, MatProgressSpinnerModule, BeitragskarteComponent],
  templateUrl: './meine-einwuerfe.component.html',
  styleUrls: ['./meine-einwuerfe.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [{ provide: MatPaginatorIntl, useClass: DeutscherPaginatorIntl }],
})
export class MeineEinwuerfeComponent implements OnInit, OnDestroy {
  /** Wie im Album; bis zu so vielen Einwuerfen gibt es keinen Paginator. */
  readonly SEITENGROESSE = 24;
  karten: KartenDaten[] = [];
  gesamt = 0;
  pageSize = this.SEITENGROESSE;
  pageIndex = 0;
  isLoading = true;
  ladefehler = false;
  /** Bis 599 px zeigt der Paginator nur Bereich und Pfeile, ohne Seitengroesse. */
  istMobil = false;

  private destroy$ = new Subject<void>();

  constructor(
    private einwurfService: EinwurfService,
    private einwurfAktionen: EinwurfAktionenService,
    private logger: LoggingService,
    private breakpointObserver: BreakpointObserver,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    this.breakpointObserver
      .observe('(max-width: 599px)')
      .pipe(takeUntil(this.destroy$))
      .subscribe((zustand) => {
        this.istMobil = zustand.matches;
        this.cdr.markForCheck();
      });
    this.laden();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  laden(): void {
    this.isLoading = true;
    this.ladefehler = false;
    this.einwurfService
      .eigeneLaden(this.pageIndex + 1, this.pageSize)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (daten) => {
          this.karten = daten.results.map(ausEinwurf);
          this.gesamt = daten.total_records_count;
          this.isLoading = false;
          this.cdr.markForCheck();
        },
        error: (error) => {
          this.logger.error('Eigene Einwürfe konnten nicht geladen werden', error);
          this.isLoading = false;
          this.ladefehler = true;
          this.cdr.markForCheck();
        },
      });
  }

  get statistik(): string {
    return `${this.gesamt} ${this.gesamt === 1 ? 'Einwurf' : 'Einwürfe'}`;
  }

  onPageChange(event: PageEvent): void {
    this.pageIndex = event.pageIndex;
    this.pageSize = event.pageSize;
    this.laden();
  }

  /** Nach dem Verwerfen dieselbe Seite neu: Die Karte zeigt dann "Verworfen". */
  aktionAusfuehren(karte: KartenDaten, aktion: EinwurfAktion): void {
    this.einwurfAktionen.ausfuehren(karte, aktion, () => this.laden(), this.destroy$);
  }

  nachKarte(_index: number, karte: KartenDaten): string {
    return karte.id;
  }
}
