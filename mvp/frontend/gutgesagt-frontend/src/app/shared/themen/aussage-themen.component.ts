import { ChangeDetectionStrategy, ChangeDetectorRef, Component, DestroyRef, Input, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { AuthService } from '../../auth/auth.service';
import { Thema } from '../../services/dtos/themenDtos';
import { AussageMitThemenFeld, ThemenService, schluesselVon } from '../../services/themen.service';
import { ThemenAuswahlComponent } from './themen-auswahl.component';
import { THEMEN_NICHT_GESPEICHERT } from './themen-meldung';

let naechsteId = 0;

/**
 * Die Themen einer Aussage als Marken, mit „Themen ändern“ bzw. „Themen zuordnen“ fuer
 * Angemeldete, auf der Ergebnisseite und unter einem Beitrag auf /beitrag/:id. Bedienung
 * wie in „Hier fehlt eine Antwort“: Der Umschalter klappt die Themenauswahl auf, jeder
 * Klick speichert gleich (ThemenService.aendern), ein Spinner zeigt das Speichern.
 * Abgemeldete sehen nur die Marken; ohne Themen zeigt die Komponente ihnen nichts.
 */
@Component({
  selector: 'app-aussage-themen',
  standalone: true,
  imports: [CommonModule, MatProgressSpinnerModule, ThemenAuswahlComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <ng-container *ngIf="aussage as a">
      <div class="aussage-themen" *ngIf="a.themen.length || bearbeitbar">
        <span *ngFor="let thema of a.themen" class="thema-marke">{{ thema.name }}</span>
        <button *ngIf="bearbeitbar" type="button" class="themen-umschalter"
                [attr.aria-expanded]="offen" [attr.aria-controls]="id"
                (click)="umschalten()">{{ a.themen.length ? 'Themen ändern' : 'Themen zuordnen' }}</button>
        <mat-spinner *ngIf="speichert" class="themen-speichert" diameter="16"
                     aria-label="Themen werden gespeichert"></mat-spinner>
      </div>
      <div *ngIf="offen && bearbeitbar" class="themen-bearbeiten" [id]="id">
        <app-themen-auswahl [themen]="liste" [gewaehlt]="gewaehlt"
                            beschriftung="Themen dieser Aussage"
                            (gewaehltChange)="setzen(a, $event)"></app-themen-auswahl>
        <p *ngIf="fehler" class="themen-fehler" role="alert">{{ fehler }}</p>
      </div>
    </ng-container>
  `,
  styles: [
    `
      :host {
        display: block;
      }

      .aussage-themen {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 6px;
      }

      /* Wie in „Hier fehlt eine Antwort“: ruhig im Hellgruen der Auswahl, 8,2:1 hell, 11,8:1 dunkel */
      .thema-marke {
        font-size: 13px;
        line-height: 1.3;
        padding: 3px 10px;
        border-radius: 999px;
        background: var(--primaer-tint);
        color: var(--akzent-schrift);
      }

      /* Nebenaktion: leise, aber als Link erkennbar (unterstrichen) */
      .themen-umschalter {
        min-height: 24px; /* Zielgroesse nach WCAG 2.5.8 */
        border: none;
        background: none;
        padding: 2px 0;
        font: inherit;
        font-size: 13px;
        color: var(--text-leise);
        text-decoration: underline;
        text-underline-offset: 3px;
        cursor: pointer;
      }

      .themen-umschalter:hover {
        color: var(--text);
      }

      .themen-umschalter:focus-visible {
        outline: 2px solid var(--akzent-tanne);
        outline-offset: 2px;
      }

      .themen-bearbeiten {
        margin-top: 8px;
      }

      .themen-fehler {
        margin: 4px 0 0;
        font-size: 13px;
        color: var(--fehler);
      }
    `,
  ],
})
export class AussageThemenComponent implements OnInit {
  /** Die Aussage mit ihren Themen; die Komponente aendert `themen` beim Speichern. */
  @Input() aussage: AussageMitThemenFeld | null = null;

  liste: Thema[] = [];
  angemeldet = false;
  offen = false;
  speichert = false;
  fehler: string | null = null;
  readonly id = `aussage-themen-${naechsteId++}`;

  constructor(
    private themenService: ThemenService,
    private authService: AuthService,
    private cdr: ChangeDetectorRef,
    private destroyRef: DestroyRef,
  ) {}

  ngOnInit(): void {
    this.authService.userInfo$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((info) => {
      this.angemeldet = !!info?.isAuthenticated;
      this.cdr.markForCheck();
    });
    this.themenService
      .liste()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (liste) => {
          this.liste = liste;
          this.cdr.markForCheck();
        },
        error: () => {
          this.liste = [];
          this.cdr.markForCheck();
        },
      });
  }

  /** Zuordnen nur angemeldet und mit geladener Liste. */
  get bearbeitbar(): boolean {
    return this.angemeldet && this.liste.length > 0;
  }

  /** Die gewaehlten Schluessel, als dasselbe Array, solange sich die Themen nicht aendern. */
  get gewaehlt(): string[] {
    const themen = this.aussage?.themen ?? [];
    if (themen !== this.zuletztThemen) {
      this.zuletztThemen = themen;
      this.zuletztSchluessel = schluesselVon(themen);
    }
    return this.zuletztSchluessel;
  }
  private zuletztThemen: Thema[] | null = null;
  private zuletztSchluessel: string[] = [];

  umschalten(): void {
    this.fehler = null;
    this.offen = !this.offen;
  }

  setzen(aussage: AussageMitThemenFeld, schluessel: string[]): void {
    this.fehler = null;
    this.speichert = true;
    this.themenService.aendern(
      aussage,
      schluessel,
      this.liste,
      () => (this.fehler = THEMEN_NICHT_GESPEICHERT),
      (offen) => {
        this.speichert = offen > 0;
        this.cdr.markForCheck();
      },
    );
  }
}
