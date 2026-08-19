import {
  Component,
  OnInit,
  OnDestroy,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { MatPaginator, PageEvent } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { BreakpointObserver } from '@angular/cdk/layout';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

import { RawInput, RawInputService, RawInputStatus } from '../services/raw-input.service';
import { LoggingService } from '../services/logging.service';

const STATUS_BESCHRIFTUNG: Record<RawInputStatus, string> = {
  open: 'Offen',
  in_progress: 'In Arbeit',
  processed: 'Verarbeitet',
  discarded: 'Verworfen',
};

/**
 * Der Fangkorb: alle Einwuerfe, neueste zuerst.
 *
 * Bewusst alle und nicht nur die eigenen - der Vorrat ist gemeinsam, und diese
 * Liste ist die Vorstufe der spaeteren Bearbeitungs-Queue. Sie kann nichts
 * ausser anzeigen: Zuweisen und Verarbeiten sind nicht gebaut.
 */
@Component({
  selector: 'app-raw-input-list',
  standalone: true,
  imports: [
    CommonModule,
    MatTableModule,
    MatPaginator,
    MatProgressSpinnerModule,
    MatButtonModule,
    MatIconModule,
  ],
  templateUrl: './raw-input-list.component.html',
  styleUrls: ['./raw-input-list.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RawInputListComponent implements OnInit, OnDestroy {
  displayedColumns: string[] = ['inhalt', 'submitted_by', 'created_at', 'status'];
  dataSource = new MatTableDataSource<RawInput>();
  totalRecords = 0;
  pageSize = 20;
  isLoading = true;
  ladefehler = false;
  isMobile = false;

  private destroy$ = new Subject<void>();

  constructor(
    private rawInputService: RawInputService,
    private router: Router,
    private logger: LoggingService,
    private cdr: ChangeDetectorRef,
    private breakpointObserver: BreakpointObserver,
  ) {}

  ngOnInit(): void {
    this.breakpointObserver
      .observe(['(max-width: 768px)'])
      .pipe(takeUntil(this.destroy$))
      .subscribe((result) => {
        this.isMobile = result.matches;
        this.cdr.markForCheck();
      });

    this.fetchData(1, this.pageSize);
  }

  fetchData(page: number, pageSize: number): void {
    this.isLoading = true;
    this.ladefehler = false;
    this.rawInputService
      .getRawInputs(page, pageSize)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (data) => {
          this.dataSource.data = data.results;
          this.totalRecords = data.total_records_count;
          this.isLoading = false;
          this.cdr.markForCheck();
        },
        error: (error) => {
          this.logger.error('Fangkorb konnte nicht geladen werden', error);
          this.isLoading = false;
          this.ladefehler = true;
          this.cdr.markForCheck();
        },
      });
  }

  onPageChange(event: PageEvent): void {
    this.fetchData(event.pageIndex + 1, event.pageSize);
  }

  /** Was in der Inhaltsspalte steht: Text, sonst Link, sonst Bild. */
  vorschau(einwurf: RawInput): string {
    return einwurf.content || einwurf.url || einwurf.image_url || '';
  }

  statusBeschriftung(status: RawInputStatus): string {
    return STATUS_BESCHRIFTUNG[status] ?? status;
  }

  /** Ohne Kennung eingeworfen - heute nur denkbar, wenn der Header fehlt. */
  einwerferBeschriftung(einwurf: RawInput): string {
    return einwurf.submitted_by || 'ohne Kennung';
  }

  zumEinwerfen(): void {
    this.router.navigate(['/einwerfen']);
  }

  navigateToStart(): void {
    this.router.navigate(['/']);
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
