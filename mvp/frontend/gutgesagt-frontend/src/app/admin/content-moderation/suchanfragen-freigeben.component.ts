import { Component, DestroyRef, Input, OnChanges, SimpleChanges, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Observable, Subject, Subscription, of } from 'rxjs';
import { filter, switchMap } from 'rxjs/operators';
import {
  SuchanfragenFreigabeService,
  ZuPruefendeSuchanfrage,
  ZuPruefendeSuchanfragenResponse,
} from '../../services/suchanfragen-freigabe.service';
import { ZuTunService } from '../../services/zu-tun.service';
import { SITZUNG_ABGELAUFEN, nachladeStrom, ohneRechte } from '../../shared/selbst-nachladen';
import {
  BestaetigungsDialogComponent,
  BestaetigungsDialogDaten,
} from '../../shared/components/bestaetigungs-dialog/bestaetigungs-dialog.component';

/** Rückfrage vor dem Freigeben (Persona-Runde 2, M1): Freigegebenes sehen alle, Rückgängig gibt es nicht. */
export const FREIGEBEN_FRAGE: BestaetigungsDialogDaten = {
  titel: 'Suchanfrage freigeben?',
  text: 'Die Suchanfrage ist danach für alle sichtbar, etwa in „Hier fehlt eine Antwort“.',
  ja: 'Freigeben',
  nein: 'Abbrechen',
};

/**
 * „Suchanfragen freigeben“ in der Moderation (Vormoderation, Entscheidung des Maintainers
 * vom 13.11.2026): Unbeantwortete Suchanfragen über der Schwelle sehen andere erst, wenn
 * ein Admin sie freigegeben hat. Die mit den meisten Personen stehen oben.
 *
 * Die Liste lädt nur, solange ihr Umschalter gewählt ist (aktiv): beim Wechsel darauf,
 * danach selbst nach (nachladeStrom: alle 30 Sekunden, solange die Seite sichtbar ist,
 * und beim Sichtbarwerden). Nach 401/403 hört sie auf und zeigt „Sitzung abgelaufen –
 * Anmelden“. Neu laden muss niemand. Die Zahl am Umschalter, in „Zu tun“ und am
 * Admin-Link kommt aus dem ZuTunService; nach einer Entscheidung stößt sie ihn an.
 */
@Component({
  selector: 'app-suchanfragen-freigeben',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatDialogModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatTooltipModule,
    RouterLink,
  ],
  template: `
    <ng-container *ngIf="aktiv">
      <p class="hinweis">
        Suchanfragen, nach denen mehrere Personen ohne Treffer gesucht haben. Andere sehen sie
        erst nach der Freigabe, etwa in „Hier fehlt eine Antwort“. Nicht freigeben, wenn der Text
        Namen, Adressen oder andere Angaben über Personen enthält.
      </p>

      <p *ngIf="sitzungAbgelaufen" class="abgelaufen" role="status" data-testid="suchanfragen-abgelaufen">
        <a routerLink="/login" [queryParams]="{ returnUrl: adresse() }">{{ sitzungAbgelaufenText }}</a>
      </p>

      <div *ngIf="suchanfragen === null && !ladefehler && !sitzungAbgelaufen" class="loading">
        <mat-spinner diameter="40"></mat-spinner>
        <p>Suchanfragen werden geladen …</p>
      </div>

      <div *ngIf="ladefehler && !sitzungAbgelaufen" class="error">
        <mat-icon>error</mat-icon>
        <p>Die Suchanfragen konnten nicht geladen werden. Es wird gleich noch einmal versucht.</p>
      </div>

      <div *ngIf="suchanfragen?.length === 0 && !ladefehler" class="empty-state">
        <mat-icon class="large-icon">check_circle</mat-icon>
        <h2>Keine Suchanfragen zu prüfen</h2>
      </div>

      <ul *ngIf="suchanfragen?.length" class="suchanfragen">
        <li *ngFor="let s of suchanfragen; trackBy: nachId" class="suchanfrage mat-elevation-z2">
          <div class="suchanfrage-text">
            <strong>„{{ s.statement_text }}“</strong>
            <span class="personen">{{ personenText(s.personen_ohne_treffer) }}</span>
          </div>
          <div class="suchanfrage-aktionen">
            <button
              mat-button
              color="primary"
              [disabled]="entscheidet.has(s.statement_id)"
              (click)="entscheiden(s, true)"
              matTooltip="Für alle sichtbar machen">
              <mat-icon>check</mat-icon>
              Freigeben
            </button>
            <button
              mat-button
              [disabled]="entscheidet.has(s.statement_id)"
              (click)="entscheiden(s, false)"
              matTooltip="Bleibt für alle außer Admins unsichtbar">
              <mat-icon>block</mat-icon>
              Ablehnen
            </button>
          </div>
        </li>
      </ul>
    </ng-container>
  `,
  styles: [
    `
      .hinweis { margin: 0 0 16px; }
      .abgelaufen { margin: 0 0 16px; font-weight: 700; }
      .loading, .error, .empty-state { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 24px 0; }
      .suchanfragen { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 12px; }
      .suchanfrage { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px; padding: 12px 16px; border-radius: 4px; }
      .suchanfrage-text { display: flex; flex-direction: column; gap: 4px; min-width: 0; overflow-wrap: anywhere; }
      .personen { opacity: 0.8; }
      .suchanfrage-aktionen { display: flex; gap: 4px; align-items: center; }
    `,
  ],
})
export class SuchanfragenFreigebenComponent implements OnChanges {
  /** Ob der Umschalter „Suchanfragen“ gewählt ist; nur dann lädt und zeigt sie die Liste. */
  @Input() aktiv = false;

  /** null, solange noch nichts geladen ist. */
  suchanfragen: ZuPruefendeSuchanfrage[] | null = null;
  ladefehler = false;
  /** Nach 401/403: Es wird nicht weiter gefragt, der Link führt zur Anmeldung. */
  sitzungAbgelaufen = false;
  readonly sitzungAbgelaufenText = SITZUNG_ABGELAUFEN;
  entscheidet = new Set<string>();
  /** In dieser Sitzung entschieden: bleibt weg, auch wenn eine ältere Antwort es noch enthält. */
  private erledigt = new Set<string>();
  /** Das Nachladen, solange die Ansicht aktiv ist. */
  private nachladen?: Subscription;
  /** Sofort laden, auch nach einem Stopp durch 401/403. */
  private readonly anstoss$ = new Subject<void>();

  private readonly service = inject(SuchanfragenFreigabeService);
  private readonly zuTun = inject(ZuTunService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly dialog = inject(MatDialog);
  private readonly destroyRef = inject(DestroyRef);

  constructor() {
    this.destroyRef.onDestroy(() => this.nachladen?.unsubscribe());
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (!changes['aktiv']) return;
    if (this.aktiv) {
      this.starten();
    } else {
      this.nachladen?.unsubscribe();
      this.nachladen = undefined;
    }
  }

  /** Sofort neu laden (etwa nach einem Fehler beim Entscheiden); nur, wenn die Ansicht aktiv ist. */
  laden(): void {
    this.anstoss$.next();
  }

  /** Wohin es nach dem Anmelden zurückgeht. */
  adresse(): string {
    return window.location.pathname + window.location.search;
  }

  private starten(): void {
    if (this.nachladen) return;
    this.sitzungAbgelaufen = false;
    this.nachladen = nachladeStrom(() => this.service.zuPruefen(true), {
      sofort: true,
      aufhoerenBei: ohneRechte,
      anstoss$: this.anstoss$,
    }).subscribe((lauf) => {
      if (lauf.fehler === null) {
        const antwort = lauf.daten as ZuPruefendeSuchanfragenResponse;
        this.suchanfragen = antwort.suchanfragen.filter((s) => !this.erledigt.has(s.statement_id));
        this.ladefehler = false;
        this.sitzungAbgelaufen = false;
      } else {
        this.ladefehler = true;
        this.sitzungAbgelaufen = ohneRechte(lauf.fehler);
      }
    });
  }

  /** Freigeben erst nach der Rückfrage (M1); Ablehnen gleich, es bleibt unsichtbar. */
  entscheiden(suchanfrage: ZuPruefendeSuchanfrage, freigeben: boolean): void {
    const id = suchanfrage.statement_id;
    this.entscheidet.add(id);
    const bestaetigt: Observable<unknown> = freigeben
      ? this.dialog
          .open(BestaetigungsDialogComponent, { data: FREIGEBEN_FRAGE, autoFocus: 'dialog' })
          .afterClosed()
      : of(true);
    bestaetigt
      .pipe(
        filter((ja) => {
          if (ja !== true) this.entscheidet.delete(id);
          return ja === true;
        }),
        switchMap(() => (freigeben ? this.service.freigeben(id) : this.service.ablehnen(id))),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: () => {
          this.erledigt.add(id);
          this.suchanfragen = (this.suchanfragen ?? []).filter((s) => s.statement_id !== id);
          this.zuTun.aktualisieren();
          this.entscheidet.delete(id);
          this.snackBar.open(freigeben ? 'Freigegeben' : 'Abgelehnt', 'OK', { duration: 3000 });
        },
        error: (fehler) => {
          this.entscheidet.delete(id);
          const text =
            fehler?.status === 404 || fehler?.status === 409
              ? 'Die Suchanfrage gibt es so nicht mehr; die Liste wird aktualisiert'
              : 'Die Entscheidung konnte nicht gespeichert werden';
          this.snackBar.open(text, 'OK', { duration: 4000 });
          this.laden();
          this.zuTun.aktualisieren();
        },
      });
  }

  personenText(personen: number): string {
    return personen === 1 ? '1 Person suchte das ohne Treffer' : `${personen} Personen suchten das ohne Treffer`;
  }

  nachId(_: number, s: ZuPruefendeSuchanfrage): string {
    return s.statement_id;
  }
}
