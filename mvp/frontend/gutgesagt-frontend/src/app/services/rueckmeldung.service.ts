import { Injectable, OnDestroy } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NavigationEnd, Router } from '@angular/router';
import { Observable, Subscription, forkJoin, of } from 'rxjs';
import { distinctUntilChanged, filter, map, switchMap, take } from 'rxjs/operators';

import { AuthService } from '../auth/auth.service';
import { UsageTrackingService } from './usage-tracking.service';
import { MeilensteinHinweisService } from '../meine-beitraege/meilenstein-hinweis.service';
import { ROUTES } from '../shared/constants/app.constants';

/** So lange steht die Rueckmeldung, wenn niemand sie wegtippt. */
const ANZEIGEDAUER_MS = 8000;

/**
 * Die Startseite, auch vor der Weiterleitung von "/" auf "/search". Dort steht der Block
 * „Seit deinem letzten Besuch“ mit derselben Zahl; die Rueckmeldung verdeckte ihn doppelt
 * (Persona-Runde 2, P51).
 */
export function istStartseite(url: string): boolean {
  const pfad = url.split(/[?#]/)[0];
  return pfad === '' || pfad === ROUTES.HOME || pfad === ROUTES.SEARCH;
}

/**
 * Die Rueckmeldung beim Anmelden (#349): "Seit deinem letzten Besuch wurden deine
 * Beitraege N-mal genutzt". Nur in der App, keine Mail und keine Push-Nachricht,
 * und nur bei N > 0.
 *
 * Bei jeder Anmeldung beginnt hier auch der Merker der Meilensteine neu (#351): Er wird
 * gelöscht und still mit allem schon Erreichten angelegt (§ 25 TDDDG, 13.11.2026).
 * Meilensteine nennt die Rückmeldung deshalb nicht; neu erreichte nennt der Hinweis
 * nach dem eigenen Tun.
 *
 * Auf der Startseite bleibt sie weg: Dort nennt der Block „Seit deinem letzten Besuch“
 * die Zahl schon (P51).
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
    private router: Router,
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
            merker: this.meilensteinHinweis.anmeldung(),
          }),
        ),
        map(({ anzahl }) => anzahl),
        filter((anzahl): anzahl is number => !!anzahl && anzahl > 0),
        // Erst, wenn feststeht, wo die App landet: vor der ersten Navigation steht router.url
        // auf "/", direkt nach der Anmeldung noch auf /login (Review).
        switchMap((anzahl) => this.zielErreicht().pipe(map(() => anzahl))),
        filter(() => !istStartseite(this.router.url)),
      )
      .subscribe((anzahl) => {
        this.snackBar.open(
          `Seit deinem letzten Besuch wurden deine Beiträge ${anzahl}-mal genutzt`,
          'OK',
          { duration: ANZEIGEDAUER_MS },
        );
      });
  }

  private zielErreicht(): Observable<unknown> {
    const unterwegs =
      !this.router.navigated || !!this.router.getCurrentNavigation() || this.router.url.startsWith('/login');
    return unterwegs
      ? this.router.events.pipe(
          filter((ereignis): ereignis is NavigationEnd => ereignis instanceof NavigationEnd),
          filter((ereignis) => !ereignis.urlAfterRedirects.startsWith('/login')),
          take(1),
        )
      : of(true);
  }

  ngOnDestroy(): void {
    this.abo?.unsubscribe();
    this.abo = undefined;
  }
}
