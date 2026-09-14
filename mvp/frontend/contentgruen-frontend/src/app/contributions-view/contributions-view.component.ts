import { Component, OnInit, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { MatPaginator, MatPaginatorIntl, PageEvent } from '@angular/material/paginator';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ContributionsService } from '../services/contributions.service';
import { ContentResult } from '../services/dtos/contributionDtos';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { UsageTrackingService, UserUsageStats } from '../services/usage-tracking.service';
import { AuthService } from '../auth/auth.service';
import { DeutscherPaginatorIntl } from '../shared/paginator-intl-de';
import { KartenlisteComponent } from '../beitragskarte/kartenliste.component';
import { KartenDaten, ausBeitrag } from '../beitragskarte/karten-daten';

/**
 * Meine Beitraege als kompakte Karten: mobil eine Liste, ab 600 px ein Raster (das
 * Layout regelt app-kartenliste per CSS). Ein Tipp sucht den Beitrag ueber seinen
 * Titel, bis es eine Detailansicht gibt.
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
export class ContributionsViewComponent implements OnInit {
  karten: KartenDaten[] = [];
  totalRecords = 0;
  pageSize = 20;
  isLoading = true;
  totalUsageCount = 0;
  userStats: UserUsageStats | null = null;

  constructor(
    private contributionsService: ContributionsService,
    private router: Router,
    private usageTrackingService: UsageTrackingService,
    private authService: AuthService,
    private cdr: ChangeDetectorRef,
  ) { }

  ngOnInit() {
    this.fetchData(1, this.pageSize);
    this.loadUserStats();
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

  calculateTotalUsage(contributions: ContentResult[]) {
    this.totalUsageCount = contributions.reduce((sum, item) => {
      return sum + (item.usage_count || 0);
    }, 0);
  }

  onPageChange(event: PageEvent) {
    this.fetchData(event.pageIndex + 1, event.pageSize);
  }

  /**
   * Uebergangsloesung wie auf der ausformulierten Fangkorb-Karte: Es gibt noch keine
   * Detailansicht (/beitrag/:id, docs/ROADMAP.md). Ohne Titel sucht der Text.
   */
  inSucheAnzeigen(karte: KartenDaten): void {
    const suche = karte.titel || karte.text;
    if (suche) {
      this.router.navigate(['/result'], { queryParams: { searchQuery: suche } });
    }
  }

  /**
   * Navigate back to the start/home page.
   */
  navigateToStart(): void {
    this.router.navigate(['/']);
  }
}
