import { ChangeDetectionStrategy, ChangeDetectorRef, Component, ElementRef, HostListener, NgZone, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subject, interval, timer } from 'rxjs';
import { filter, switchMap, takeUntil } from 'rxjs/operators';

import { PUNKTE_NICHT_GELADEN, Punktestand, UsageTrackingService } from '../services/usage-tracking.service';

/** So oft lädt die Seite den Punktestand nach, solange sie sichtbar ist. */
export const PUNKTE_NACHLADEN_MS = 60_000;
/** Erst nach so langer Wartezeit erscheint der Platzhalter, damit nichts aufblitzt. */
export const PUNKTE_PLATZHALTER_MS = 1_000;

/**
 * Der eigene Punktestand in „Meine Beiträge“ (#352, ADR 0004): gesamt und je Stufe.
 * Nur die Person selbst sieht ihn (Datenschutzerklärung „Punkte“); Ranglisten kommen
 * später mit eigener Zustimmung.
 *
 * Punkte entstehen vor allem dadurch, dass andere die Beiträge nutzen; die Seite lädt
 * den Stand deshalb selbst nach: beim Zurückkehren in den Tab und, solange der Bereich
 * sichtbar ist (nicht hinter dem Tab „Meine Einwürfe“), jede Minute. Der Pfad steht
 * deshalb nicht im Cache (auth/cache.interceptor.ts).
 *
 * Nichts zu sehen bei ausgeschalteten Punkten (404) und für Konten, die keine Punkte
 * sammeln (Startkonto, keine Art.-9-Einwilligung). Scheitert ein Nachladen anders,
 * bleibt der letzte Stand stehen.
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
  /** Stand noch unbekannt und schon eine Weile gewartet: Platzhalter zeigen. */
  platzhalter = false;
  private bekannt = false;
  private laden$ = new Subject<void>();
  private destroy$ = new Subject<void>();

  constructor(
    private usageTrackingService: UsageTrackingService,
    private cdr: ChangeDetectorRef,
    private zone: NgZone,
    private host: ElementRef<HTMLElement>,
  ) {}

  ngOnInit(): void {
    // switchMap: Eine neue Anfrage ersetzt eine noch laufende, der Stand bleibt der neueste.
    this.laden$
      .pipe(
        switchMap(() => this.usageTrackingService.getEigenePunkte()),
        takeUntil(this.destroy$),
      )
      .subscribe((antwort) => {
        if (antwort === PUNKTE_NICHT_GELADEN) {
          return;
        }
        this.punkte = antwort?.sammelt === false ? null : antwort;
        this.bekannt = true;
        this.platzhalter = false;
        this.cdr.markForCheck();
      });
    // Takte laufen ausserhalb der Angular-Zone, sonst wird die Anwendung nie
    // "stable"; nur was sie ausloesen, laeuft wieder in der Zone.
    this.zone.runOutsideAngular(() => {
      interval(PUNKTE_NACHLADEN_MS)
        .pipe(
          filter(() => document.visibilityState === 'visible' && !this.verborgen),
          takeUntil(this.destroy$),
        )
        .subscribe(() => this.zone.run(() => this.laden$.next()));
      timer(PUNKTE_PLATZHALTER_MS)
        .pipe(
          filter(() => !this.bekannt),
          takeUntil(this.destroy$),
        )
        .subscribe(() =>
          this.zone.run(() => {
            this.platzhalter = true;
            this.cdr.markForCheck();
          }),
        );
    });
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

  /** Hinter einem anderen Tab von „Meine Beiträge“ (`[hidden]`) fragt die Seite nicht nach. */
  private get verborgen(): boolean {
    return this.host.nativeElement.closest('[hidden]') !== null;
  }
}
