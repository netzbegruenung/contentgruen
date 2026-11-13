import { ChangeDetectionStrategy, ChangeDetectorRef, Component, DestroyRef, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { HttpErrorResponse } from '@angular/common/http';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Observable, of } from 'rxjs';
import { catchError, map, switchMap, tap } from 'rxjs/operators';

import { BeitragskarteComponent } from '../beitragskarte/beitragskarte.component';
import { KartenDaten, ausEinzelansicht } from '../beitragskarte/karten-daten';
import { AussageKurz, ContentService, WeitereAntwort } from '../services/content.service';
import { BeitragKontextComponent } from './beitrag-kontext.component';
import { LoggingService } from '../services/logging.service';
import { ROUTES } from '../shared/constants/app.constants';

type Zustand = 'laedt' | 'da' | 'nichtDa' | 'stoerung';

/** Die Aussage und weitere Antworten unter der Karte (#603). */
interface Kontext {
  aussage: AussageKurz | null;
  weitere: WeitereAntwort[];
}

const OHNE_KONTEXT: Kontext = { aussage: null, weitere: [] };

export const NICHT_VERFUEGBAR = 'Dieser Beitrag ist nicht verfügbar.';
export const NICHT_ANZEIGBAR = 'Der Beitrag lässt sich gerade nicht anzeigen.';

/**
 * Ein Beitrag unter seiner eigenen Adresse, /beitrag/:id (#300), fuer alle
 * Beitragstypen. Dorthin fuehren "Beitrag öffnen" im Menue der Karte (Suche, Album,
 * nach dem Speichern) und "Ansehen" an einem ausformulierten Einwurf.
 *
 * Mit Abstimmen wie in der Suche (Entscheidung @BanSe 03.11.): Der Endpunkt liefert
 * die eigene Stimme mit (user_vote), sonst zeigte die Karte eine falsche.
 * Gesperrte und geloeschte Beitraege gibt es hier fuer niemanden (404).
 *
 * "Teilen" an der Karte selbst (B7, vorher "Link kopieren" unter ihr): so teilt sie die
 * angezeigte Fassung, zaehlt sie mit und zeigt die neue Nutzung. Unter der Karte die Aussage, auf die der
 * Beitrag antwortet, und weitere Antworten zu ihr (#603, app-beitrag-kontext); der
 * Endpunkt liefert Aussage und Antworten mit.
 */
@Component({
  selector: 'app-beitrag-ansicht',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    MatButtonModule,
    MatProgressSpinnerModule,
    BeitragskarteComponent,
    BeitragKontextComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="beitrag-ansicht">
      <div *ngIf="zustand === 'laedt'" class="laedt">
        <mat-spinner diameter="32"></mat-spinner>
      </div>

      <app-beitragskarte *ngIf="karte as karte" [daten]="karte" variante="voll"
                         [ansichtVerlinkt]="false" [teilbar]="true"></app-beitragskarte>
      <app-beitrag-kontext *ngIf="karte" [aussage]="kontext.aussage"
                           [weitere]="kontext.weitere"></app-beitrag-kontext>

      <ng-container *ngIf="zustand === 'nichtDa' || zustand === 'stoerung'">
        <p class="hinweis" role="status">{{ zustand === 'nichtDa' ? nichtVerfuegbar : nichtAnzeigbar }}</p>
        <a mat-stroked-button class="zur-suche" [routerLink]="suche">Zur Suche</a>
      </ng-container>
    </div>
  `,
  styles: [
    `
      .beitrag-ansicht {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 16px;
        /* Spalte so breit wie die Karte, linksbuendig im Seitenrahmen (styles.css) */
        max-width: calc(450px + 2 * var(--page-margin));
        box-sizing: border-box; /* kein globales border-box: sonst kaeme der Rand auf max-width */
        padding: 16px var(--page-margin);
      }

      app-beitragskarte {
        display: block;
        width: 100%;
      }

      .laedt {
        padding: 24px 0;
      }

      .hinweis {
        margin: 0;
        color: var(--text-secondary);
        text-align: center;
      }
    `,
  ],
})
export class BeitragAnsichtComponent implements OnInit {
  zustand: Zustand = 'laedt';
  karte: KartenDaten | null = null;
  kontext: Kontext = OHNE_KONTEXT;

  readonly nichtVerfuegbar = NICHT_VERFUEGBAR;
  readonly nichtAnzeigbar = NICHT_ANZEIGBAR;
  readonly suche = ROUTES.SEARCH;

  constructor(
    private route: ActivatedRoute,
    private contentService: ContentService,
    private logger: LoggingService,
    private cdr: ChangeDetectorRef,
    private destroyRef: DestroyRef,
  ) {}

  ngOnInit(): void {
    this.route.paramMap
      .pipe(
        map((params) => params.get('id') ?? ''),
        tap((id) => {
          this.zustand = 'laedt';
          this.karte = null;
          this.cdr.markForCheck();
        }),
        switchMap((id) => this.laden(id)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe(({ zustand, karte, kontext }) => {
        this.zustand = zustand;
        this.karte = karte;
        this.kontext = kontext;
        this.cdr.markForCheck();
      });
  }

  private laden(id: string): Observable<{ zustand: Zustand; karte: KartenDaten | null; kontext: Kontext }> {
    return this.contentService.beitragLaden(id).pipe(
      map((beitrag) => ({
        zustand: 'da' as Zustand,
        karte: ausEinzelansicht(beitrag),
        kontext: { aussage: beitrag.aussage ?? null, weitere: beitrag.weitere_antworten ?? [] },
      })),
      catchError((fehler: HttpErrorResponse) => {
        // 404 ist erwartbar (alter Link, gesperrt, geloescht), 422 eine ID, die keine ist.
        if (fehler?.status === 404 || fehler?.status === 422) {
          return of({ zustand: 'nichtDa' as Zustand, karte: null, kontext: OHNE_KONTEXT });
        }
        this.logger.warn('Beitrag zur Adresse nicht ladbar', fehler);
        return of({ zustand: 'stoerung' as Zustand, karte: null, kontext: OHNE_KONTEXT });
      }),
    );
  }
}
