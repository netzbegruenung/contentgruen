import { ChangeDetectionStrategy, ChangeDetectorRef, Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { Subject, forkJoin } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

import { AbzeichenSichtbarkeit, Meilenstein, UsageTrackingService } from '../services/usage-tracking.service';

/**
 * Die eigenen Meilensteine in „Meine Beiträge“ (#351): erreichte als Abzeichen, die
 * übrigen mit Stand („3/10“).
 *
 * Darunter die Zustimmung zur Sichtbarkeit (GLOSSARY.md): Ab dem ersten erreichten
 * Meilenstein fragt die Seite einmal mit zwei gleichwertigen Knöpfen, ob andere
 * Angemeldete das Abzeichen am Namen sehen; nichts ist vorbelegt, die Antwort lässt
 * sich jederzeit ändern (ADR 0004, docs/VISION.md). Ohne die Schalter liefert der
 * Server keine Sichtbarkeit, dann fragt die Seite nicht und die Meilensteine bleiben
 * nur für die Person.
 *
 * Ohne Meilensteine (Punkte ausgeschaltet, Startkonto, keine Art.-9-Einwilligung)
 * zeigt die Komponente nichts.
 */
@Component({
  selector: 'app-meilensteine',
  standalone: true,
  imports: [CommonModule, MatButtonModule],
  templateUrl: './meilensteine.component.html',
  styleUrls: ['./meilensteine.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MeilensteineComponent implements OnInit, OnDestroy {
  meilensteine: Meilenstein[] = [];
  sichtbarkeit: AbzeichenSichtbarkeit | null = null;
  speichert = false;
  /** Nach einem Nein erneut gefragt ("Anderen zeigen"): Zustimmen nur mit dem Wortlaut vor Augen. */
  frageOffen = false;
  fehler = false;
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
    forkJoin({
      meilensteine: this.usageTrackingService.getEigeneMeilensteine(),
      sichtbarkeit: this.usageTrackingService.getAbzeichenSichtbarkeit(),
    })
      .pipe(takeUntil(this.destroy$))
      .subscribe(({ meilensteine, sichtbarkeit }) => {
        this.meilensteine = meilensteine;
        this.sichtbarkeit = sichtbarkeit;
        this.cdr.markForCheck();
      });
  }

  get erreichte(): number {
    return this.meilensteine.filter((m) => m.erreicht).length;
  }

  /** Einmal fragen, sobald es etwas zu zeigen gäbe. */
  get fragen(): boolean {
    if (!this.sichtbarkeit) {
      return false;
    }
    return this.frageOffen || (!this.sichtbarkeit.gefragt && this.erreichte > 0);
  }

  /** Andere Angemeldete sehen das Abzeichen. */
  get sichtbar(): boolean {
    return this.sichtbarkeit?.zeigen === true;
  }

  /** "Anderen zeigen" fragt noch einmal mit dem Wortlaut; "Nicht mehr zeigen" gilt sofort. */
  aendern(): void {
    if (this.sichtbar) {
      this.antworten(false);
    } else {
      this.frageOffen = true;
    }
  }

  antworten(zeigen: boolean): void {
    const stand = this.sichtbarkeit;
    if (!stand || this.speichert) {
      return;
    }
    this.speichert = true;
    this.fehler = false;
    this.usageTrackingService
      .setAbzeichenSichtbarkeit(zeigen, stand.aktueller_wortlaut.kennung)
      .pipe(takeUntil(this.destroy$))
      .subscribe((ok) => {
        this.speichert = false;
        if (ok) {
          this.sichtbarkeit = { ...stand, gefragt: true, zeigen };
          this.frageOffen = false;
        } else {
          this.fehler = true;
        }
        this.cdr.markForCheck();
      });
  }
}
