import { ChangeDetectionStrategy, ChangeDetectorRef, Component, HostListener, NgZone, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subject, interval } from 'rxjs';
import { filter, switchMap, takeUntil } from 'rxjs/operators';

import { Punktestand, UsageTrackingService } from '../services/usage-tracking.service';

/** So oft lädt die Seite den Punktestand nach, solange sie sichtbar ist. */
export const PUNKTE_NACHLADEN_MS = 60_000;

/**
 * Der eigene Punktestand in „Meine Beiträge“ (#352, ADR 0004): gesamt und je Stufe.
 * Nur die Person selbst sieht ihn (Datenschutzerklärung „Punkte“); Ranglisten kommen
 * später mit eigener Zustimmung.
 *
 * Punkte entstehen vor allem dadurch, dass andere die Beiträge nutzen; die Seite lädt
 * den Stand deshalb selbst nach: beim Zurückkehren in den Tab und, solange die Seite
 * sichtbar ist, jede Minute.
 *
 * Bei ausgeschalteten Punkten (404) oder einem Fehler zeigt die Komponente nichts.
 * Startkonten und Konten ohne Art.-9-Einwilligung bekommen 0 Punkte.
 */
@Component({
  selector: 'app-punkte',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './punkte.component.html',
  styleUrls: ['./punkte.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PunkteComponent implements OnInit, OnDestroy {
  punkte: Punktestand | null = null;
  private laden$ = new Subject<void>();
  private destroy$ = new Subject<void>();

  constructor(
    private usageTrackingService: UsageTrackingService,
    private cdr: ChangeDetectorRef,
    private zone: NgZone,
  ) {}

  ngOnInit(): void {
    // switchMap: Eine neue Anfrage ersetzt eine noch laufende, der Stand bleibt der neueste.
    this.laden$
      .pipe(
        switchMap(() => this.usageTrackingService.getEigenePunkte()),
        takeUntil(this.destroy$),
      )
      .subscribe((punkte) => {
        this.punkte = punkte;
        this.cdr.markForCheck();
      });
    // Der Takt laeuft ausserhalb der Angular-Zone, sonst wird die Anwendung nie
    // "stable"; nur das Nachladen selbst laeuft wieder in der Zone.
    this.zone.runOutsideAngular(() =>
      interval(PUNKTE_NACHLADEN_MS)
        .pipe(
          filter(() => document.visibilityState === 'visible'),
          takeUntil(this.destroy$),
        )
        .subscribe(() => this.zone.run(() => this.laden$.next())),
    );
    this.laden$.next();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  /** Zurück im Tab: gleich den neuen Stand holen, nicht erst beim nächsten Takt. */
  @HostListener('document:visibilitychange')
  onVisibilityChange(): void {
    if (document.visibilityState === 'visible') {
      this.laden$.next();
    }
  }
}
