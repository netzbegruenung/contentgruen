import { ChangeDetectionStrategy, ChangeDetectorRef, Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

import { Sperrnachricht, SperrnachrichtService } from '../services/sperrnachricht.service';
import { sperrgrundLabel } from '../shared/sperrgruende';
import { LEGAL_ENTITY } from '../shared/legal-entity';

/** Höchstlänge eines Widerspruchs, wie im Suchdienst. */
export const WIDERSPRUCH_MAX = 2000;

/**
 * Die Sperrnachrichten oben in „Meine Beiträge“ (#448): je gesperrtem eigenen Beitrag
 * Entscheidung, Sperrgrund, Begründung und der Weg zum Widerspruch, danach der Stand
 * der erneuten Prüfung, auch „aufgehoben“ (dann ist der Beitrag wieder im Album). Ohne
 * Sperre zeigt die Komponente nichts.
 *
 * Gesperrte Beiträge selbst stehen nicht im Album; nur hier erfährt die Person von
 * der Sperre (Nutzungsbedingungen Abschnitt 7).
 */
@Component({
  selector: 'app-sperrnachrichten',
  standalone: true,
  imports: [CommonModule, FormsModule, MatButtonModule, MatFormFieldModule, MatInputModule],
  templateUrl: './sperrnachrichten.component.html',
  styleUrls: ['./sperrnachrichten.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SperrnachrichtenComponent implements OnInit, OnDestroy {
  readonly KONTAKT_MAIL = LEGAL_ENTITY.KONTAKT_MAIL;
  readonly WIDERSPRUCH_MAX = WIDERSPRUCH_MAX;
  nachrichten: Sperrnachricht[] = [];
  /** Die Sperre, deren Widerspruchsfeld offen ist. */
  widerspruchFuer: string | null = null;
  widerspruchText = '';
  sendet = false;
  fehler: string | null = null;

  private destroy$ = new Subject<void>();

  constructor(
    private sperrnachrichtService: SperrnachrichtService,
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
    this.sperrnachrichtService
      .meine()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (nachrichten) => {
          this.nachrichten = nachrichten;
          this.cdr.markForCheck();
        },
        // Ohne Sperrnachrichten bleibt das Album benutzbar; der Fehler steht im Log.
        error: (fehler) => console.error('Sperrnachrichten nicht geladen:', fehler),
      });
  }

  sperrgrund(wert: string): string {
    return sperrgrundLabel(wert);
  }

  datum(zeitpunkt: string | null): string {
    return zeitpunkt ? new Date(zeitpunkt).toLocaleDateString('de-DE') : '';
  }

  widerspruchOeffnen(nachricht: Sperrnachricht): void {
    this.widerspruchFuer = nachricht.id;
    this.widerspruchText = '';
    this.fehler = null;
  }

  widerspruchAbbrechen(): void {
    this.widerspruchFuer = null;
    this.fehler = null;
  }

  widersprechen(nachricht: Sperrnachricht): void {
    this.sendet = true;
    this.fehler = null;
    this.sperrnachrichtService
      .widersprechen(nachricht.id, this.widerspruchText)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.sendet = false;
          this.widerspruchFuer = null;
          this.laden();
        },
        error: (fehler) => {
          this.sendet = false;
          // 409: Es gibt schon einen Widerspruch, etwa aus einem zweiten Tab.
          if (fehler?.status === 409) {
            this.widerspruchFuer = null;
            this.laden();
          } else {
            this.fehler = 'Der Widerspruch ging nicht raus. Bitte versuch es noch einmal.';
          }
          this.cdr.markForCheck();
        },
      });
  }
}
