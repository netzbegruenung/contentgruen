import {
  Component,
  DestroyRef,
  EventEmitter,
  Inject,
  Input,
  NgZone,
  OnChanges,
  OnInit,
  Output,
  SimpleChanges,
} from '@angular/core';
import { CommonModule, DOCUMENT } from '@angular/common';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Observable, Subscription, fromEvent, interval, of } from 'rxjs';
import { filter, switchMap } from 'rxjs/operators';
import {
  SuchanfragenFreigabeService,
  ZuPruefendeSuchanfrage,
} from '../../services/suchanfragen-freigabe.service';
import {
  BestaetigungsDialogComponent,
  BestaetigungsDialogDaten,
} from '../../shared/components/bestaetigungs-dialog/bestaetigungs-dialog.component';

/** So oft lädt die Liste nach, solange die Seite sichtbar ist. */
export const NACHLADEN_MS = 30_000;

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
 * Die Komponente bleibt eingehängt, auch wenn ein anderer Umschalter gewählt ist, damit
 * die Zahl am Umschalter stimmt: Sie lädt beim Einhängen, beim Wechsel auf ihren
 * Umschalter (aktiv), wenn die Seite wieder sichtbar wird, und alle 30 Sekunden, solange
 * die Seite sichtbar ist. Neu laden muss niemand. Ist ihr Umschalter nicht gewählt, holt
 * sie nur die Zahl, nicht die Liste.
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
  ],
  template: `
    <ng-container *ngIf="aktiv">
      <p class="hinweis">
        Suchanfragen, nach denen mehrere Personen ohne Treffer gesucht haben. Andere sehen sie
        erst nach der Freigabe, etwa in „Hier fehlt eine Antwort“. Nicht freigeben, wenn der Text
        Namen, Adressen oder andere Angaben über Personen enthält.
      </p>

      <div *ngIf="suchanfragen === null && !ladefehler" class="loading">
        <mat-spinner diameter="40"></mat-spinner>
        <p>Suchanfragen werden geladen …</p>
      </div>

      <div *ngIf="ladefehler" class="error">
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
      .loading, .error, .empty-state { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 24px 0; }
      .suchanfragen { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 12px; }
      .suchanfrage { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px; padding: 12px 16px; border-radius: 4px; }
      .suchanfrage-text { display: flex; flex-direction: column; gap: 4px; min-width: 0; overflow-wrap: anywhere; }
      .personen { opacity: 0.8; }
      .suchanfrage-aktionen { display: flex; gap: 4px; align-items: center; }
    `,
  ],
})
export class SuchanfragenFreigebenComponent implements OnInit, OnChanges {
  /** Ob der Umschalter „Suchanfragen“ gewählt ist; nur dann zeigt sie die Liste. */
  @Input() aktiv = false;
  /** Die Zahl der zu prüfenden Suchanfragen, für den Umschalter. */
  @Output() anzahl = new EventEmitter<number>();

  /** null, solange noch nichts geladen ist. */
  suchanfragen: ZuPruefendeSuchanfrage[] | null = null;
  ladefehler = false;
  entscheidet = new Set<string>();
  /** In dieser Sitzung entschieden: bleibt weg, auch wenn eine ältere Antwort es noch enthält. */
  private erledigt = new Set<string>();
  private laden$?: Subscription;

  constructor(
    private service: SuchanfragenFreigabeService,
    private snackBar: MatSnackBar,
    private dialog: MatDialog,
    private destroyRef: DestroyRef,
    private zone: NgZone,
    @Inject(DOCUMENT) private document: Document,
  ) {}

  ngOnInit(): void {
    this.laden();
    // Der Takt läuft außerhalb der Zone, damit die Seite für Tests und Werkzeuge, die auf
    // Ruhe warten, ruhig wird; jedes Nachladen läuft wieder in der Zone.
    this.zone.runOutsideAngular(() =>
      interval(NACHLADEN_MS)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe(() => {
          if (this.sichtbar()) {
            this.zone.run(() => this.laden());
          }
        }),
    );
    fromEvent(this.document, 'visibilitychange')
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        if (this.sichtbar()) {
          this.laden();
        }
      });
  }

  ngOnChanges(changes: SimpleChanges): void {
    const aktiv = changes['aktiv'];
    if (aktiv && !aktiv.firstChange && aktiv.currentValue) {
      this.laden();
    }
  }

  laden(): void {
    // Eine noch laufende Anfrage ersetzen, damit keine ältere Antwort die neuere überschreibt.
    this.laden$?.unsubscribe();
    if (!this.aktiv) {
      this.laden$ = this.service
        .anzahl()
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: (antwort) => this.anzahlMelden(antwort.anzahl),
          // Die Zahl bleibt dann stehen; der nächste Takt versucht es wieder.
          error: () => undefined,
        });
      return;
    }
    this.laden$ = this.service
      .zuPruefen()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (antwort) => {
          this.suchanfragen = antwort.suchanfragen.filter((s) => !this.erledigt.has(s.statement_id));
          this.ladefehler = false;
          this.anzahlMelden();
        },
        error: () => {
          this.ladefehler = true;
        },
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
          this.anzahlMelden();
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
        },
      });
  }

  personenText(personen: number): string {
    return personen === 1 ? '1 Person suchte das ohne Treffer' : `${personen} Personen suchten das ohne Treffer`;
  }

  nachId(_: number, s: ZuPruefendeSuchanfrage): string {
    return s.statement_id;
  }

  /**
   * Die Zahl erst nach dem laufenden Prüfdurchlauf melden: Die Zahl steht am Umschalter
   * über dieser Komponente, und eine Antwort, die sofort kommt, änderte sie sonst
   * mitten im Durchlauf der Elternkomponente.
   */
  private anzahlMelden(anzahl = this.suchanfragen?.length ?? 0): void {
    Promise.resolve().then(() => this.anzahl.emit(anzahl));
  }

  private sichtbar(): boolean {
    return this.document.visibilityState !== 'hidden';
  }
}
