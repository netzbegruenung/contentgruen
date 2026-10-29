import { Injectable, OnDestroy } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Subscription } from 'rxjs';
import { distinctUntilChanged, filter, map, switchMap } from 'rxjs/operators';

import { AuthService } from '../auth/auth.service';
import { UsageTrackingService } from './usage-tracking.service';

/** So lange steht die Rueckmeldung, wenn niemand sie wegtippt. */
const ANZEIGEDAUER_MS = 8000;

/**
 * Die Rueckmeldung beim Anmelden (#349): "Seit deinem letzten Besuch wurden deine
 * Beitraege N-mal genutzt". Nur in der App, keine Mail und keine Push-Nachricht,
 * und nur bei N > 0.
 *
 * Gefragt wird einmal je angemeldeter Person und App-Start: Die Anmeldedaten kommen
 * oft zweimal (erst aus der Login-Antwort, dann aus /api/user-info), deshalb zaehlt
 * nur ein Wechsel der Kennung. Jede Frage gilt dem Backend als Besuch und schreibt
 * den gezeigten Stand fort.
 */
@Injectable({ providedIn: 'root' })
export class RueckmeldungService implements OnDestroy {
  private abo?: Subscription;

  constructor(
    private authService: AuthService,
    private usageTrackingService: UsageTrackingService,
    private snackBar: MatSnackBar,
  ) {}

  /** Einmal beim App-Start aufrufen; weitere Aufrufe tun nichts. */
  starten(): void {
    if (this.abo) {
      return;
    }
    this.abo = this.authService.userInfo$
      .pipe(
        map((info) => (info?.isAuthenticated ? info.userId : null)),
        distinctUntilChanged(),
        filter((kennung): kennung is string => !!kennung),
        switchMap(() => this.usageTrackingService.besuchMelden()),
        filter((anzahl): anzahl is number => !!anzahl && anzahl > 0),
      )
      .subscribe((anzahl) => {
        this.snackBar.open(
          `Seit deinem letzten Besuch wurden deine Beiträge ${anzahl}-mal genutzt`,
          'OK',
          { duration: ANZEIGEDAUER_MS },
        );
      });
  }

  ngOnDestroy(): void {
    this.abo?.unsubscribe();
    this.abo = undefined;
  }
}
