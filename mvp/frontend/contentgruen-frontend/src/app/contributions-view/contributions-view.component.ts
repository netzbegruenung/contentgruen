import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { BreakpointObserver } from '@angular/cdk/layout';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { MatPaginator, MatPaginatorIntl, PageEvent } from '@angular/material/paginator';
import { MatBottomSheet } from '@angular/material/bottom-sheet';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ContributionsService } from '../services/contributions.service';
import { ContentResult } from '../services/dtos/contributionDtos';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { UsageTrackingService, UserUsageStats } from '../services/usage-tracking.service';
import { AuthService } from '../auth/auth.service';
import { DeutscherPaginatorIntl } from '../shared/paginator-intl-de';
import { KartenlisteComponent } from '../beitragskarte/kartenliste.component';
import { BeitragSheetComponent } from '../beitragskarte/beitrag-sheet.component';
import { KartenDaten, ausBeitrag } from '../beitragskarte/karten-daten';

/**
 * Meine Beitraege als Album: kompakte, hochkante Karten im Raster (2/3/4 Spalten, das
 * Layout regelt app-kartenliste per CSS), darueber die Statistik als eine Textzeile.
 * Ein Tipp oeffnet den Beitrag als volle Karte im Bottom Sheet, mit Aktionsleiste und
 * Herkunft; eine Suche und damit eine neue Suchaussage entsteht dabei nicht.
 */
@Component({
  selector: 'app-contributions-view',
  standalone: true,
  imports: [
    CommonModule,
    MatPaginator,
    MatProgressSpinnerModule,
    KartenlisteComponent
  ],
  templateUrl: './contributions-view.component.html',
  styleUrls: ['./contributions-view.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  // Hier und nicht in app.config.ts: dort zoege der Import den Paginator samt
  // Abhaengigkeiten ins initiale Bundle, obwohl nur diese Route ihn nutzt.
  providers: [{ provide: MatPaginatorIntl, useClass: DeutscherPaginatorIntl }]
})
export class ContributionsViewComponent implements OnInit, OnDestroy {
  karten: KartenDaten[] = [];
  /** Bis 599 px zeigt der Paginator nur Bereich und Pfeile, ohne Seitengroesse. */
  istMobil = false;
  private destroy$ = new Subject<void>();
  totalRecords = 0;
  /** Standard-Seitengroesse; bis zu so vielen Beitraegen gibt es keinen Paginator. */
  readonly SEITENGROESSE = 24;
  pageSize = this.SEITENGROESSE;
  /** Gebunden, damit der Paginator die Seite auch ueber ein Neuzeichnen hinweg haelt. */
  pageIndex = 0;
  isLoading = true;
  totalUsageCount = 0;
  userStats: UserUsageStats | null = null;

  constructor(
    private contributionsService: ContributionsService,
    private router: Router,
    private usageTrackingService: UsageTrackingService,
    private authService: AuthService,
    private cdr: ChangeDetectorRef,
    private breakpointObserver: BreakpointObserver,
    private bottomSheet: MatBottomSheet,
  ) { }

  ngOnInit() {
    this.breakpointObserver
      .observe('(max-width: 599px)')
      .pipe(takeUntil(this.destroy$))
      .subscribe((zustand) => {
        this.istMobil = zustand.matches;
        this.cdr.markForCheck();
      });

    this.fetchData(1, this.pageSize);
    this.loadUserStats();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  fetchData(page: number, pageSize: number) {
    this.isLoading = true;
    this.contributionsService.getContributions(page, pageSize).subscribe((data) => {
      this.karten = data.results.map((eintrag) => ausBeitrag(eintrag));
      this.totalRecords = data.total_records_count;
      this.calculateTotalUsage(data.results);
      this.isLoading = false;
      this.cdr.markForCheck();
    });
  }

  loadUserStats() {
    const userId = this.authService.getCurrentUserId();
    if (userId) {
      this.usageTrackingService.getUserUsageStats(userId).subscribe(stats => {
        this.userStats = stats;
        this.cdr.markForCheck();
      });
    }
  }

  /** "2 Beiträge · 3× genutzt": Nutzung ueber alle Seiten, sonst die Summe dieser Seite. */
  get statistik(): string {
    const beitraege = this.totalRecords === 1 ? 'Beitrag' : 'Beiträge';
    const nutzung = this.userStats?.total_usage_count ?? this.totalUsageCount;
    return `${this.totalRecords} ${beitraege} · ${nutzung}× genutzt`;
  }

  calculateTotalUsage(contributions: ContentResult[]) {
    this.totalUsageCount = contributions.reduce((sum, item) => {
      return sum + (item.usage_count || 0);
    }, 0);
  }

  onPageChange(event: PageEvent) {
    this.pageIndex = event.pageIndex;
    this.pageSize = event.pageSize;
    this.fetchData(this.pageIndex + 1, this.pageSize);
  }

  /** Oeffnet den Beitrag als volle Karte; schliessen per Wisch, Klick ausserhalb oder Escape. */
  beitragOeffnen(karte: KartenDaten): void {
    this.bottomSheet.open(BeitragSheetComponent, {
      data: karte,
      ariaLabel: karte.titel || karte.text || 'Beitrag',
    });
  }

  /**
   * Navigate back to the start/home page.
   */
  navigateToStart(): void {
    this.router.navigate(['/']);
  }
}
