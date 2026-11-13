import { Injectable, OnDestroy } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Subscription, forkJoin } from 'rxjs';
import { distinctUntilChanged, filter, map, switchMap } from 'rxjs/operators';

import { AuthService } from '../auth/auth.service';
import { UsageTrackingService } from './usage-tracking.service';
import { MeilensteinHinweisService, meilensteinText } from '../meine-beitraege/meilenstein-hinweis.service';

/** So lange steht die Rueckmeldung, wenn niemand sie wegtippt. */
const ANZEIGEDAUER_MS = 8000;

/**
 * Die Rueckmeldung beim Anmelden (#349): "Seit deinem letzten Besuch wurden deine
 * Beitraege N-mal genutzt". Nur in der App, keine Mail und keine Push-Nachricht,
 * und nur bei N > 0 oder einem neu erreichten Meilenstein (#351): Den nennt sie beim
 * Namen, mit „Ansehen“ zu Meine Beiträge. Ohne eingeschaltete Punkte gibt es keine
 * Meilensteine, dann bleibt es bei der Nutzung.
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
    private meilensteinHinweis: MeilensteinHinweisService,
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
        switchMap(() =>
          forkJoin({
            anzahl: this.usageTrackingService.besuchMelden(),
            neu: this.meilensteinHinweis.neueErreichte(),
          }),
        ),
      )
      .subscribe(({ anzahl, neu }) => {
        const genutzt = anzahl && anzahl > 0 ? `Seit deinem letzten Besuch wurden deine Beiträge ${anzahl}-mal genutzt` : null;
        if (!neu.length) {
          if (genutzt) {
            this.snackBar.open(genutzt, 'OK', { duration: ANZEIGEDAUER_MS });
          }
          return;
        }
        const meilenstein = meilensteinText(neu);
        this.meilensteinHinweis.zeigen(genutzt ? `${genutzt}. ${meilenstein}` : meilenstein);
        this.meilensteinHinweis.merken(neu);
      });
  }

  ngOnDestroy(): void {
    this.abo?.unsubscribe();
    this.abo = undefined;
  }
}
