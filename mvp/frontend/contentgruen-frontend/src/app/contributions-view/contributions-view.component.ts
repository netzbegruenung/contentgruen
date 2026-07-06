import { Component, OnInit, ChangeDetectionStrategy, ChangeDetectorRef, OnDestroy } from '@angular/core';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { MatPaginator, PageEvent } from '@angular/material/paginator';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ContributionsService } from '../services/contributions.service';
import { ContentResult } from '../services/dtos/contributionDtos';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { UsageTrackingService, UserUsageStats } from '../services/usage-tracking.service';
import { AuthService } from '../auth/auth.service';
import { BreakpointObserver } from '@angular/cdk/layout';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

@Component({
  selector: 'app-contributions-view',
  standalone: true,
  imports: [
    CommonModule,
    MatTableModule,
    MatPaginator,
    MatProgressSpinnerModule,
    MatButtonModule,
    MatIconModule
  ],
  templateUrl: './contributions-view.component.html',
  styleUrls: ['./contributions-view.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ContributionsViewComponent implements OnInit, OnDestroy {
  displayedColumns: string[] = ['content_type', 'text', 'usage_count', 'created', 'last_modified', 'last_modified_by'];
  dataSource = new MatTableDataSource<ContentResult>();
  totalRecords = 0;
  pageSize = 20;
  isLoading = true;
  totalUsageCount = 0;
  userStats: UserUsageStats | null = null;
  isMobile: boolean = false;
  private destroy$ = new Subject<void>();

  constructor(
    private contributionsService: ContributionsService,
    private router: Router,
    private usageTrackingService: UsageTrackingService,
    private authService: AuthService,
    private cdr: ChangeDetectorRef,
    private breakpointObserver: BreakpointObserver
  ) { }

  ngOnInit() {
    // Set up responsive breakpoint detection
    this.breakpointObserver.observe(['(max-width: 768px)'])
      .pipe(takeUntil(this.destroy$))
      .subscribe(result => {
        this.isMobile = result.matches;
        this.cdr.markForCheck();
      });

    this.fetchData(1, this.pageSize);
    this.loadUserStats();
  }

  fetchData(page: number, pageSize: number) {
    this.isLoading = true;
    this.contributionsService.getContributions(page, pageSize).subscribe((data) => {
      this.dataSource.data = data.results;
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
   * Navigate back to the start/home page.
   */
  navigateToStart(): void {
    this.router.navigate(['/']);
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
