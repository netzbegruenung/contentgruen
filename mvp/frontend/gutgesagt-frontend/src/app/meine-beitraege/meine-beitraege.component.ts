import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { BreakpointObserver } from '@angular/cdk/layout';
import { Subject } from 'rxjs';
import { filter, takeUntil } from 'rxjs/operators';
import { MatPaginator, MatPaginatorIntl, PageEvent } from '@angular/material/paginator';
import { MatBottomSheet } from '@angular/material/bottom-sheet';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { MEINE_TAB_PARAM } from '../services/navigation.service';
import { MeineBeitraegeService } from '../services/meine-beitraege.service';
import { ContentResult } from '../services/dtos/contributionDtos';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { UsageTrackingService, UserUsageStats } from '../services/usage-tracking.service';
import { AuthService } from '../auth/auth.service';
import { DeutscherPaginatorIntl } from '../shared/paginator-intl-de';
import { KartenlisteComponent } from '../beitragskarte/kartenliste.component';
import { BeitragSheetComponent, BeitragSheetDaten, GEAENDERT, GELOESCHT } from '../beitragskarte/beitrag-sheet.component';
import { istAenderbar } from '../beitragskarte/beitrag-aendern-dialog.component';
import { KartenDaten, ausBeitrag } from '../beitragskarte/karten-daten';
import { MeineEinwuerfeComponent } from './meine-einwuerfe.component';
import { SperrnachrichtenComponent } from './sperrnachrichten.component';
import { MeilensteineComponent } from './meilensteine.component';
import { tabMitTasteWaehlen } from '../shared/tab-tasten';
import { MatButtonModule } from '@angular/material/button';
import { ROUTES } from '../shared/constants/app.constants';

/** Die beiden Tabs: eigene Beitraege und "Meine Einwuerfe". */
export type MeineTab = 'beitraege' | 'einwuerfe';

const TABS: ReadonlyArray<{ wert: MeineTab; name: string }> = [
  { wert: 'beitraege', name: 'Meine Beiträge' },
  { wert: 'einwuerfe', name: 'Meine Einwürfe' },
];

/**
 * Meine Beitraege als Album: kompakte, hochkante Karten im Raster (2/3/4 Spalten, das
 * Layout regelt app-kartenliste per CSS), darueber die Statistik als eine Textzeile.
 * Ein Tipp oeffnet den Beitrag als volle Karte im Bottom Sheet, mit Aktionsleiste und
 * Herkunft; eine Suche und damit eine neue Suchaussage entsteht dabei nicht.
 *
 * Der zweite Tab ist "Meine Einwuerfe" (app-meine-einwuerfe): was aus den eigenen
 * Einwuerfen geworden ist. Er laedt erst beim ersten Oeffnen.
 */
@Component({
  selector: 'app-meine-beitraege',
  standalone: true,
  imports: [
    CommonModule,
    MatPaginator,
    MatProgressSpinnerModule,
    MatButtonModule,
    KartenlisteComponent,
    MeineEinwuerfeComponent,
    SperrnachrichtenComponent,
    MeilensteineComponent
  ],
  templateUrl: './meine-beitraege.component.html',
  styleUrls: ['../shared/tabs.css', './meine-beitraege.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  // Hier und nicht in app.config.ts: dort zoege der Import den Paginator samt
  // Abhaengigkeiten ins initiale Bundle, obwohl nur diese Route ihn nutzt.
  providers: [{ provide: MatPaginatorIntl, useClass: DeutscherPaginatorIntl }]
})
export class MeineBeitraegeComponent implements OnInit, OnDestroy {
  readonly tabs = TABS;
  tab: MeineTab = 'beitraege';
  /** Ab dem ersten Oeffnen bleibt der Einwurf-Tab stehen, damit Wechseln nicht neu laedt. */
  einwuerfeGeoeffnet = false;
  karten: KartenDaten[] = [];
  /** Bis 599 px zeigt der Paginator nur Bereich und Pfeile, ohne Seitengroesse. */
  istMobil = false;
  private destroy$ = new Subject<void>();
  totalRecords = 0;
  /** Standard-Seitengroesse; bis zu so vielen Beitraegen gibt es keinen Paginator. */
  readonly SEITENGROESSE = 24;
  pageSize = this.SEITENGROESSE;
  /** Gebunden, damit der Paginator die Seite auch ueber ein Neuzeichnen hinweg haelt. */
  pageIndex = 0;
  isLoading = true;
  totalUsageCount = 0;
  nutzungsstatistik: UserUsageStats | null = null;

  constructor(
    private meineBeitraegeService: MeineBeitraegeService,
    private router: Router,
    private route: ActivatedRoute,
    private usageTrackingService: UsageTrackingService,
    private authService: AuthService,
    private cdr: ChangeDetectorRef,
    private breakpointObserver: BreakpointObserver,
    private bottomSheet: MatBottomSheet,
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
    this.breakpointObserver
      .observe('(max-width: 599px)')
      .pipe(takeUntil(this.destroy$))
      .subscribe((zustand) => {
        this.istMobil = zustand.matches;
        this.cdr.markForCheck();
      });

    this.fetchData(1, this.pageSize);
    this.nutzungsstatistikLaden();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  fetchData(page: number, pageSize: number) {
    this.isLoading = true;
    this.meineBeitraegeService.meineBeitraege(page, pageSize).subscribe((data) => {
      this.karten = data.results.map((eintrag) => ausBeitrag(eintrag));
      this.totalRecords = data.total_records_count;
      this.calculateTotalUsage(data.results);
      this.isLoading = false;
      this.cdr.markForCheck();
    });
  }

  nutzungsstatistikLaden() {
    if (this.authService.getCurrentUserId()) {
      this.usageTrackingService.getEigeneNutzungsstatistik().subscribe(stats => {
        this.nutzungsstatistik = stats;
        this.cdr.markForCheck();
      });
    }
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

  /** "2 Beiträge · 3× genutzt": Nutzung ueber alle Seiten, sonst die Summe dieser Seite. */
  get statistik(): string {
    const beitraege = this.totalRecords === 1 ? 'Beitrag' : 'Beiträge';
    const nutzung = this.nutzungsstatistik?.total_usage_count ?? this.totalUsageCount;
    return `${this.totalRecords} ${beitraege} · ${nutzung}× genutzt`;
  }

  calculateTotalUsage(beitraege: ContentResult[]) {
    this.totalUsageCount = beitraege.reduce((sum, item) => {
      return sum + (item.usage_count || 0);
    }, 0);
  }

  onPageChange(event: PageEvent) {
    this.pageIndex = event.pageIndex;
    this.pageSize = event.pageSize;
    this.fetchData(this.pageIndex + 1, this.pageSize);
  }

  /**
   * Oeffnet den Beitrag als volle Karte; schliessen per Wisch, Klick ausserhalb oder Escape.
   * Hier stehen nur eigene Beitraege, deshalb darf das Sheet loeschen und, bei Kommentar
   * und Hintergrundinfo, aendern (#299). Danach laedt die Seite neu, samt Statistik; war
   * der geloeschte der letzte Beitrag der Seite, die Seite davor.
   */
  beitragOeffnen(karte: KartenDaten): void {
    const daten: BeitragSheetDaten = {
      ...karte,
      loeschbar: true,
      aenderbar: istAenderbar(karte.typ),
      zurAdresse: true,
    };
    this.bottomSheet
      .open(BeitragSheetComponent, {
        data: daten,
        ariaLabel: karte.titel || karte.text || 'Beitrag',
      })
      .afterDismissed()
      .pipe(filter((ergebnis) => ergebnis === GELOESCHT || ergebnis === GEAENDERT))
      .subscribe((ergebnis) => {
        if (ergebnis === GELOESCHT && this.karten.length === 1 && this.pageIndex > 0) {
          this.pageIndex--;
        }
        this.fetchData(this.pageIndex + 1, this.pageSize);
        this.nutzungsstatistikLaden();
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
