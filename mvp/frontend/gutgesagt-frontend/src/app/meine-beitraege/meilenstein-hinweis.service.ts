import { Inject, Injectable, OnDestroy } from '@angular/core';
import { Router } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Observable, Subject, Subscription, of } from 'rxjs';
import { debounceTime, map, switchMap } from 'rxjs/operators';

import { AuthService } from '../auth/auth.service';
import { Meilenstein, UsageTrackingService } from '../services/usage-tracking.service';
import { ROUTES } from '../shared/constants/app.constants';
import { MEILENSTEIN_MERKER } from '../shared/geraetespeicher-schalter';
import { gesehenMerken, merkerLesen } from './meilenstein-merker';

/** So lange steht der Hinweis, wenn niemand ihn wegtippt; wie die Rückmeldung (#349). */
const ANZEIGEDAUER_MS = 8000;

/**
 * So lange sammelt pruefen() Aufrufe: Ausformulieren speichert einen Beitrag und
 * verknüpft den Einwurf, beides ruft pruefen() auf; daraus wird ein Hinweis.
 */
export const SAMMELN_MS = 300;

/** „Meilenstein erreicht: Erster Einwurf“ oder „2 Meilensteine erreicht“. */
export function meilensteinText(neu: Meilenstein[]): string {
  return neu.length === 1 ? `Meilenstein erreicht: ${neu[0].name}` : `${neu.length} Meilensteine erreicht`;
}

/**
 * Ein kurzer Hinweis direkt nach dem eigenen Tun (Einwerfen, Ausformulieren, einen
 * Kommentar speichern oder einen vorhandenen nehmen) oder beim Anmelden, wenn ein
 * Meilenstein neu erreicht wurde (#351).
 *
 * Was schon angezeigt wurde, merkt sich nur der Browser je Konto
 * (meilenstein-merker.ts), und zwar erst, wenn es wirklich angezeigt wurde. Gibt es
 * noch keinen Eintrag (neuer Browser, nach dem Abmelden), gilt alles schon Erreichte
 * still als gesehen: Genannt wird nur, was danach neu dazukommt. Kein
 * Server-Eintrag, keine Mail, kein Push. Kein Countdown, keine Serie, keine
 * Erinnerung; wer „Meine Beiträge“ öffnet, hat alles gesehen. Ohne eingeschaltete
 * Punkte liefert der Server keine Meilensteine, dann passiert hier nichts.
 *
 * Solange MEILENSTEIN_MERKER aus ist (§ 25 TDDDG in Prüfung), gibt es weder Merker noch
 * Hinweise: neueErreichte liefert nichts, ohne Anfrage und ohne Speicherzugriff, und
 * eine Bestätigung kommt als normale Snackbar.
 */
@Injectable({ providedIn: 'root' })
export class MeilensteinHinweisService implements OnDestroy {
  private anstoesse = new Subject<void>();
  private abo: Subscription;
  /** Eine Bestätigung, die mit einem Meilenstein in eine Snackbar zusammengeht. */
  private bestaetigung: { text: string; aktion: string; dauer: number } | null = null;

  constructor(
    private usageTrackingService: UsageTrackingService,
    private authService: AuthService,
    private snackBar: MatSnackBar,
    private router: Router,
    @Inject(MEILENSTEIN_MERKER) private merkerAktiv: boolean,
  ) {
    // Mehrere Anstöße kurz hintereinander ergeben eine Abfrage und einen Hinweis.
    this.abo = this.anstoesse
      .pipe(
        debounceTime(SAMMELN_MS),
        switchMap(() => this.neueErreichte()),
      )
      .subscribe((neu) => {
        const bestaetigung = this.bestaetigung;
        this.bestaetigung = null;
        if (neu.length) {
          const meilenstein = meilensteinText(neu);
          this.zeigen(bestaetigung ? `${bestaetigung.text} ${meilenstein}` : meilenstein);
          this.merken(neu);
        } else if (bestaetigung) {
          this.snackBar.open(bestaetigung.text, bestaetigung.aktion, { duration: bestaetigung.dauer });
        }
      });
  }

  ngOnDestroy(): void {
    this.abo.unsubscribe();
  }

  /**
   * Die erreichten, noch nicht angezeigten Meilensteine. Gemerkt werden sie erst mit
   * merken(), nachdem sie angezeigt wurden. Ohne Konto oder Speicher eine leere Liste,
   * ohne Anfrage.
   */
  neueErreichte(): Observable<Meilenstein[]> {
    if (!this.merkerAktiv || !merkerLesen(this.authService.getCurrentUserId())) {
      return of([]);
    }
    return this.usageTrackingService.getEigeneMeilensteine().pipe(
      map((meilensteine) => {
        const kennung = this.authService.getCurrentUserId();
        const merker = merkerLesen(kennung);
        if (!merker) {
          return [];
        }
        if (!merker.vorhanden) {
          // Erster Abruf in diesem Browser: still anlegen, nichts nennen.
          gesehenMerken(kennung, meilensteine);
          return [];
        }
        return meilensteine.filter((m) => m.erreicht && !merker.gesehen.has(m.kennung));
      }),
    );
  }

  /** Diese Meilensteine als angezeigt merken. */
  merken(meilensteine: Meilenstein[]): void {
    if (!this.merkerAktiv) {
      return;
    }
    gesehenMerken(this.authService.getCurrentUserId(), meilensteine);
  }

  /** Nach einer gespeicherten Handlung aufrufen; Aufrufe kurz hintereinander zählen einmal. */
  pruefen(): void {
    if (this.merkerAktiv) {
      this.anstoesse.next();
    }
  }

  /**
   * Eine Bestätigung zeigen; ist dabei ein Meilenstein neu, in derselben Snackbar,
   * damit der Hinweis die Bestätigung nicht verdrängt.
   */
  bestaetigen(text: string, aktion = 'OK', dauer = 5000): void {
    if (!this.merkerAktiv) {
      this.snackBar.open(text, aktion, { duration: dauer });
      return;
    }
    this.bestaetigung = { text, aktion, dauer };
    this.anstoesse.next();
  }

  /** Ein Hinweis mit „Ansehen“, das zu Meine Beiträge führt. */
  zeigen(text: string): void {
    this.snackBar
      .open(text, 'Ansehen', { duration: ANZEIGEDAUER_MS })
      .onAction()
      .subscribe(() => this.ansehen());
  }

  ansehen(): void {
    this.router.navigateByUrl(ROUTES.MEINE_BEITRAEGE);
  }
}
