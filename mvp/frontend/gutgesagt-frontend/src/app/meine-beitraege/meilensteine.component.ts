import { ChangeDetectionStrategy, ChangeDetectorRef, Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

import { Meilenstein, UsageTrackingService } from '../services/usage-tracking.service';

/**
 * Die eigenen Meilensteine in „Meine Beiträge“ (#351): erreichte als Abzeichen, die
 * übrigen mit Stand („3/10“). Nur die Person selbst sieht sie; ein Abzeichen am
 * Anzeigenamen für andere braucht eine eigene Zustimmung zur Sichtbarkeit
 * (ADR 0004, docs/VISION.md „Meilensteine“) und kommt mit ihr.
 *
 * Ohne Meilensteine (Punkte ausgeschaltet, Startkonto, keine Art.-9-Einwilligung)
 * zeigt die Komponente nichts.
 */
@Component({
  selector: 'app-meilensteine',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './meilensteine.component.html',
  styleUrls: ['./meilensteine.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MeilensteineComponent implements OnInit, OnDestroy {
  meilensteine: Meilenstein[] = [];
  private destroy$ = new Subject<void>();

  constructor(
    private usageTrackingService: UsageTrackingService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    this.laden();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  laden(): void {
    this.usageTrackingService
      .getEigeneMeilensteine()
      .pipe(takeUntil(this.destroy$))
      .subscribe((meilensteine) => {
        this.meilensteine = meilensteine;
        this.cdr.markForCheck();
      });
  }

  get erreichte(): number {
    return this.meilensteine.filter((m) => m.erreicht).length;
  }
}
