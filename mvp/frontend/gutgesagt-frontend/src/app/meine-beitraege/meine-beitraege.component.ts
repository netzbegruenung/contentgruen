import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { Observable, Subject, of } from 'rxjs';
import { catchError, map, switchMap, takeUntil } from 'rxjs/operators';
import { MatSnackBar } from '@angular/material/snack-bar';
import { AlleMeineBeitraege } from '../services/meine-beitraege.service';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MEINE_TAB_PARAM } from '../services/navigation.service';
import { MeineBeitraegeService } from '../services/meine-beitraege.service';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Meilenstein, UsageTrackingService } from '../services/usage-tracking.service';
import { BeitragVerwaltenService } from '../beitragskarte/beitrag-verwalten.service';
import { KartenDaten } from '../beitragskarte/karten-daten';
import { MeineEinwuerfeComponent } from './meine-einwuerfe.component';
import { SperrnachrichtenComponent } from './sperrnachrichten.component';
import { MeilensteineComponent } from './meilensteine.component';
import { PunkteComponent } from './punkte.component';
import { tabMitTasteWaehlen } from '../shared/tab-tasten';
import { MatButtonModule } from '@angular/material/button';
import { ROUTES } from '../shared/constants/app.constants';
import { StatementService } from '../services/statement.service';
import { UnbeantworteteAussage } from '../services/dtos/statementDtos';
import { beantwortenParamsJeAussage } from '../hier-fehlt-eine-antwort/hier-fehlt-eine-antwort.component';
import { FORMULAR_PFAD } from '../shared/formular-adresse';
import { AussagekarteComponent } from '../shared/aussagekarte/aussagekarte.component';
import { AlbumComponent } from './album/album.component';
import { AlbumEintrag, albumEintrag, naechsterMeilenstein } from './album/album';

/** So viele unbeantwortete Aussagen zeigt der leere Zustand als ersten Schritt (#645). */
export const ERSTE_SCHRITTE = 3;

/** Die beiden Tabs: eigene Beitraege und "Meine Einwuerfe". */
export type MeineTab = 'beitraege' | 'einwuerfe';

const TABS: ReadonlyArray<{ wert: MeineTab; name: string }> = [
  { wert: 'beitraege', name: 'Meine Beiträge' },
  { wert: 'einwuerfe', name: 'Meine Einwürfe' },
];

/**
 * Meine Beitraege als Album nach Thema (Variante A, Sebastian und Aila 20.11.; app-album):
 * alle eigenen Beitraege auf einmal, als volle Karten in Abschnitten je Thema, oben der
 * Deckel mit Zahlen und Wirkungssatz, darueber eine Suche ueber die eigenen Beitraege.
 * Aendern und Loeschen gehen direkt an der Karte; danach laedt die Liste still nach,
 * aufgeklappte Abschnitte bleiben offen.
 *
 * Der zweite Tab ist "Meine Einwuerfe" (app-meine-einwuerfe): was aus den eigenen
 * Einwuerfen geworden ist. Er laedt erst beim ersten Oeffnen.
 */
@Component({
  selector: 'app-meine-beitraege',
  standalone: true,
  imports: [
    CommonModule,
    MatProgressSpinnerModule,
    MatButtonModule,
    RouterLink,
    AlbumComponent,
    MeineEinwuerfeComponent,
    SperrnachrichtenComponent,
    MeilensteineComponent,
    PunkteComponent,
    AussagekarteComponent
  ],
  templateUrl: './meine-beitraege.component.html',
  styleUrls: ['../shared/tabs.css', '../shared/aussagekarte/aussagekarten.scss', './meine-beitraege.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MeineBeitraegeComponent implements OnInit, OnDestroy {
  readonly tabs = TABS;
  tab: MeineTab = 'beitraege';
  /** Ab dem ersten Oeffnen bleibt der Einwurf-Tab stehen, damit Wechseln nicht neu laedt. */
  einwuerfeGeoeffnet = false;
  eintraege: AlbumEintrag[] = [];
  private destroy$ = new Subject<void>();
  /** Nur beim ersten Laden; danach laedt die Liste still nach und bleibt stehen. */
  isLoading = true;
  ladefehler = false;
  /** Der naechste offene Meilenstein fuer den Deckel; null ohne Meilensteine. */
  naechsterMeilenstein: Meilenstein | null = null;
  /** Ohne eigene Beitraege: die ersten unbeantworteten Aussagen aus "Hier fehlt eine Antwort" (#645). */
  unbeantworteteAussagen: UnbeantworteteAussage[] = [];
  readonly kommentarFormular = FORMULAR_PFAD.commentary;
  readonly hierFehltEineAntwortPfad = ROUTES.HIER_FEHLT_EINE_ANTWORT;
  readonly beantwortenParams = beantwortenParamsJeAussage();

  constructor(
    private meineBeitraegeService: MeineBeitraegeService,
    private router: Router,
    private route: ActivatedRoute,
    private usageTrackingService: UsageTrackingService,
    private cdr: ChangeDetectorRef,
    private statementService: StatementService,
    private verwalten: BeitragVerwaltenService,
    private snackBar: MatSnackBar,
  ) { }

  ngOnInit() {
    // Ein Tab in der Adresse, etwa nach dem Ausformulieren "Meine Einwuerfe" (#508).
    const tab = TABS.find((eintrag) => eintrag.wert === this.route.snapshot.queryParamMap.get(MEINE_TAB_PARAM));
    if (tab) {
      this.tabWaehlen(tab.wert);
      // Der Tab gilt nur fuer diesen Sprung: Bliebe er in der Adresse, oeffnete ein
      // Neuladen nach dem Wechsel zu "Meine Beitraege" wieder "Meine Einwuerfe".
      this.router.navigate([], {
        relativeTo: this.route,
        queryParams: { [MEINE_TAB_PARAM]: null },
        queryParamsHandling: 'merge',
        replaceUrl: true,
      });
    }
    this.ladenAbonnieren();
    this.laden();
    this.meilensteinLaden();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  /**
   * Alle eigenen Beitraege; beim Nachladen bleibt die bisherige Liste stehen, bis die neue da
   * ist. Zwei schnelle Nachladungen ueberholen sich nicht: Es gilt die letzte (switchMap).
   * Scheitert das erste Laden, steht ein Hinweis mit neuem Versuch da; scheitert ein
   * Nachladen, sagt es eine Meldung, und die Liste bleibt, wie sie ist.
   */
  laden(): void {
    this.laden$.next();
  }

  private readonly laden$ = new Subject<void>();

  private ladenAbonnieren(): void {
    this.laden$
      .pipe(
        switchMap(() =>
          this.meineBeitraegeService.alleMeineBeitraege().pipe(
            map((antwort): AlleMeineBeitraege | null => antwort),
            catchError((): Observable<AlleMeineBeitraege | null> => of(null)),
          ),
        ),
        takeUntil(this.destroy$),
      )
      .subscribe((antwort) => {
        const erstes = this.isLoading;
        this.isLoading = false;
        if (antwort === null) {
          this.ladefehler = !this.eintraege.length;
          if (!erstes && this.eintraege.length) {
            this.snackBar.open('Deine Beiträge ließen sich gerade nicht aktualisieren.', 'OK', { duration: 5000 });
          }
        } else {
          this.eintraege = antwort.beitraege.map(albumEintrag);
          this.ladefehler = false;
          if (!this.eintraege.length) {
            this.unbeantworteteLaden();
          }
        }
        this.cdr.markForCheck();
      });
  }

  /** Fuer den Deckel: der offene Meilenstein, dem die Person am naechsten ist (naechsterMeilenstein). */
  private meilensteinLaden(): void {
    this.usageTrackingService
      .getEigeneMeilensteine()
      .pipe(takeUntil(this.destroy$))
      .subscribe((meilensteine) => {
        this.naechsterMeilenstein = naechsterMeilenstein(meilensteine);
        this.cdr.markForCheck();
      });
  }

  /**
   * Der erste Schritt im leeren Zustand: unbeantwortete Aussagen zum direkten Antworten, in der
   * Reihenfolge von "Hier fehlt eine Antwort". Scheitert das Laden, bleibt nur "Beitragen".
   */
  private unbeantworteteLaden(): void {
    this.statementService.unbeantworteteAussagen().pipe(takeUntil(this.destroy$)).subscribe({
      next: (aussagen) => {
        this.unbeantworteteAussagen = aussagen.slice(0, ERSTE_SCHRITTE);
        this.cdr.markForCheck();
      },
      error: () => {
        this.unbeantworteteAussagen = [];
        this.cdr.markForCheck();
      },
    });
  }

  tabWaehlen(tab: MeineTab): void {
    this.tab = tab;
    this.einwuerfeGeoeffnet ||= tab === 'einwuerfe';
  }

  /** Pfeiltasten, Pos1 und Ende waehlen den Tab und setzen den Fokus mit. */
  tabTaste(event: KeyboardEvent): void {
    const jetzt = this.tabs.findIndex((eintrag) => eintrag.wert === this.tab);
    tabMitTasteWaehlen(event, jetzt, this.tabs.length, (ziel) => this.tabWaehlen(this.tabs[ziel].wert));
  }

  /** "Ändern" an einer Karte (#299): nach dem Speichern laedt die Liste still nach. */
  aendern(karte: KartenDaten): void {
    this.verwalten.aendern(karte).pipe(takeUntil(this.destroy$)).subscribe((gespeichert) => {
      if (gespeichert) {
        this.laden();
      }
    });
  }

  /** "Beitrag löschen" im ⋮-Menue (#250): nach der Rueckfrage; ist er weg, laedt die Liste nach. */
  loeschen(karte: KartenDaten): void {
    this.verwalten.loeschen(karte.id).pipe(takeUntil(this.destroy$)).subscribe((weg) => {
      if (weg) {
        // Sofort aus der Liste, nicht erst nach dem Nachladen: Scheitert das, ist die Karte trotzdem weg.
        this.eintraege = this.eintraege.filter((e) => e.karte.id !== karte.id);
        this.cdr.markForCheck();
        this.laden();
        this.meilensteinLaden();
      }
    });
  }

  /** Aus dem leeren Zustand ein Weg weiter (#512). */
  zumBeitragen(): void {
    this.router.navigate([ROUTES.CONTRIBUTE]);
  }

  /**
   * Navigate back to the start/home page.
   */
  navigateToStart(): void {
    this.router.navigate(['/']);
  }
}
