import {
  Component,
  OnInit,
  OnDestroy,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  ElementRef,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { BreakpointObserver } from '@angular/cdk/layout';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

import { EinwurfAktionenService } from './einwurf-aktionen.service';

import { Einwurf, EinwurfService } from '../services/einwurf.service';
import { LoggingService } from '../services/logging.service';
import { Plattform, PLATTFORMEN } from '../shared/plattform';
import { FANGKORB_BESCHREIBUNG } from '../shared/fangkorb-texte';
import { BeitragskarteComponent } from '../beitragskarte/beitragskarte.component';
import { KartenDaten, EinwurfAktion, ausEinwurf } from '../beitragskarte/karten-daten';
import { HilfeUmschalterComponent } from '../shared/components/hilfe-umschalter/hilfe-umschalter.component';
import { TabAusrichtung, tabMitTasteWaehlen } from '../shared/tab-tasten';
import { LadeWiederholung } from '../shared/lade-wiederholung';
import {
  FangkorbFilter,
  FangkorbTab,
  TABS,
  filterLaden,
  filterSpeichern,
  passtZumFilter,
  passtZumTab,
} from './fangkorb-filter';

/**
 * So viele Einwuerfe laedt der Fangkorb auf einmal - mehr gibt der Endpunkt je
 * Seite nicht her. Gefiltert, sortiert und gezaehlt wird im Browser; liegen mehr
 * im Fangkorb, sagt die Liste das dazu.
 */
export const LADE_GROESSE = 100;

/**
 * Ab dieser Breite steht der Fangkorb in zwei Spalten: links die Seitenleiste mit
 * Einwerfen, Arbeitslisten (senkrecht) und Filtern, rechts die Liste mit queren
 * Karten. Darunter bleibt alles wie am Handy. Eine Quelle fuer Layout und
 * Tastatur: Das CSS haengt an der Klasse, die dieser Wert setzt.
 */
export const SEITENLEISTE_MEDIEN = '(min-width: 1024px)';

/**
 * Der Fangkorb: zwei Tabs, die Arbeitslisten, benannt nach der naechsten Arbeit,
 * in jedem die Einwuerfe, an denen dort etwas zu tun ist.
 *
 * Destillieren = offen (noch kein Satz), Ausformulieren = destilliert (Saetze ohne
 * Beitrag). Ausformuliertes (mit mindestens einem Beitrag verknuepft) hat keine
 * Arbeit mehr und steht nicht hier, sondern unter "Meine Einwuerfe". Verworfenes
 * liegt hinter einem Chip im Tab seiner naechsten Arbeit. Welcher Tab gilt,
 * entscheidet ``passtZumTab``; die Chips (Plattform, "nur meine", "verworfen")
 * wirken quer dazu und gelten auch fuer die Zaehler.
 *
 * Bewusst alle Einwuerfe und nicht nur die eigenen - der Vorrat ist gemeinsam.
 * Sortiert wird hier neueste zuerst, nicht in der Reihenfolge des Servers
 * (eigene zuerst): im Fangkorb zaehlt das Alter, nicht die Person.
 */
@Component({
  selector: 'app-fangkorb',
  standalone: true,
  imports: [CommonModule, MatProgressSpinnerModule, MatButtonModule, MatIconModule, BeitragskarteComponent, HilfeUmschalterComponent],
  templateUrl: './fangkorb.component.html',
  styleUrls: ['../shared/tabs.css', './fangkorb.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FangkorbComponent implements OnInit, OnDestroy {
  readonly plattformen = PLATTFORMEN;
  readonly tabs = TABS;
  readonly fangkorbBeschreibung = FANGKORB_BESCHREIBUNG;

  /** Die Langfassung hinter dem Hilfe-Icon; zu, bis jemand danach fragt. */
  erklaerungOffen = false;
  einwuerfe: Einwurf[] = [];
  /** Was die Chips uebrig lassen, neueste zuerst - die Grundlage der Zaehler. */
  gefiltert: Einwurf[] = [];
  sichtbar: Einwurf[] = [];
  /** Die sichtbaren Einwuerfe als Karten, einmal je Filterlauf berechnet. */
  karten: KartenDaten[] = [];
  zaehler: Record<FangkorbTab, number> = { destillieren: 0, ausformulieren: 0 };
  gesamt = 0;
  filter: FangkorbFilter = filterLaden();
  isLoading = true;
  ladefehler = false;
  /** Nach einem Ladefehler: ein neuer Versuch laeuft gerade. */
  erneutLaedt = false;
  /** Nach einem Ladefehler: Die Seite versucht es von selbst weiter (lohntWiederholung). */
  versuchtWeiter = false;
  /**
   * Was die Live-Region ansagt: nur der erste Fehler und die Rueckkehr, nicht jeder
   * Versuch dazwischen. Die Region steht immer im DOM, damit Screenreader sie kennen.
   */
  ansage = '';
  /** Breit genug fuer die Seitenleiste (SEITENLEISTE_MEDIEN). */
  seitenleiste = false;

  private destroy$ = new Subject<void>();
  /** Nach einem Ladefehler: der naechste Versuch, selbst geplant. */
  private wiederholung = new LadeWiederholung(this.destroy$);

  constructor(
    private einwurfService: EinwurfService,
    private router: Router,
    private logger: LoggingService,
    private cdr: ChangeDetectorRef,
    private einwurfAktionen: EinwurfAktionenService,
    private breakpoints: BreakpointObserver,
    private host: ElementRef<HTMLElement>,
  ) {}

  ngOnInit(): void {
    this.breakpoints
      .observe(SEITENLEISTE_MEDIEN)
      .pipe(takeUntil(this.destroy$))
      .subscribe((stand) => {
        this.seitenleiste = stand.matches;
        this.cdr.markForCheck();
      });
    this.laden();
  }

  /**
   * Laedt den Fangkorb. Nach einem Fehler bleibt die Meldung stehen, waehrend der
   * naechste Versuch laeuft; der Spinner kommt nur, solange noch nichts gescheitert ist.
   */
  laden(): void {
    this.wiederholung.abbrechen();
    if (this.ladefehler) {
      this.erneutLaedt = true;
    } else {
      this.isLoading = true;
    }
    this.cdr.markForCheck();
    this.einwurfService
      .fangkorbLaden(1, LADE_GROESSE)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (daten) => {
          const nachFehler = this.ladefehler;
          const fokusAmKnopf = this.fokusAmErneutKnopf();
          this.einwuerfe = daten.results;
          this.gesamt = daten.total_records_count;
          this.isLoading = false;
          this.ladefehler = false;
          this.erneutLaedt = false;
          this.wiederholung.erfolg();
          if (nachFehler) {
            this.ansage = 'Fangkorb wieder geladen.';
          }
          this.filtern();
          if (fokusAmKnopf) {
            this.fokusInDieListe();
          }
        },
        error: (error) => {
          this.logger.error('Fangkorb konnte nicht geladen werden', error);
          if (!this.ladefehler) {
            this.ansage = 'Der Fangkorb konnte gerade nicht geladen werden.';
          }
          this.isLoading = false;
          this.ladefehler = true;
          this.erneutLaedt = false;
          this.versuchtWeiter = this.wiederholung.fehlgeschlagen(error, () => this.laden());
          this.cdr.markForCheck();
        },
      });
  }

  /**
   * "Erneut versuchen": sofort, statt auf den geplanten Versuch zu warten. Waehrend
   * ein Versuch laeuft, ist der Knopf nur aria-disabled (er behaelt den Fokus) und
   * tut nichts.
   */
  erneutVersuchen(): void {
    if (this.erneutLaedt) {
      return;
    }
    this.laden();
  }

  // Tabs

  tabWaehlen(tab: FangkorbTab): void {
    this.filterSetzen({ ...this.filter, tab });
  }

  /** In der Seitenleiste stehen die Tabs untereinander, sonst nebeneinander. */
  get tabAusrichtung(): TabAusrichtung {
    return this.seitenleiste ? 'vertical' : 'horizontal';
  }

  /**
   * Pfeiltasten (nebeneinander links/rechts, untereinander hoch/runter), Pos1 und
   * Ende waehlen den Tab und setzen den Fokus mit.
   */
  tabTaste(event: KeyboardEvent): void {
    const jetzt = TABS.findIndex((eintrag) => eintrag.wert === this.filter.tab);
    tabMitTasteWaehlen(event, jetzt, TABS.length, (ziel) => this.tabWaehlen(TABS[ziel].wert), this.tabAusrichtung);
  }

  /** Die Zeile im leeren Tab: erst gar nichts da, dann die Chips, dann der Tab. */
  get leerText(): string {
    if (this.gesamt === 0) {
      return 'Noch nichts drin. Wirf den ersten Fund ein.';
    }
    if (!this.gefiltert.length) {
      return 'Keine Einwürfe für diese Filter.';
    }
    return TABS.find((eintrag) => eintrag.wert === this.filter.tab)!.leer;
  }

  // Filter

  plattformAktiv(plattform: Plattform): boolean {
    return this.filter.plattformen.includes(plattform);
  }

  /** Alle Plattformen eingeblendet heisst: kein Plattform-Filter. */
  get allePlattformenAktiv(): boolean {
    return PLATTFORMEN.every((eintrag) => this.plattformAktiv(eintrag.wert));
  }

  /**
   * Gefuellt ist ein Chip nur, wenn er wirklich filtert. Ohne Filter sehen alle
   * Chips aus wie "nur meine" im Ruhezustand.
   */
  plattformGewaehlt(plattform: Plattform): boolean {
    return !this.allePlattformenAktiv && this.plattformAktiv(plattform);
  }

  /**
   * Ohne Filter waehlt ein Tipp genau diese Plattform. Mit Filter schaltet er sie
   * dazu oder weg; wird die letzte abgewaehlt, gilt wieder kein Filter.
   */
  plattformUmschalten(plattform: Plattform): void {
    const alle = PLATTFORMEN.map((eintrag) => eintrag.wert);
    let plattformen: Plattform[];
    if (this.allePlattformenAktiv) {
      plattformen = [plattform];
    } else {
      const gewaehlt = this.plattformAktiv(plattform);
      plattformen = alle.filter((wert) => (wert === plattform ? !gewaehlt : this.plattformAktiv(wert)));
      if (!plattformen.length) {
        plattformen = alle;
      }
    }
    this.filterSetzen({ ...this.filter, plattformen });
  }

  nurMeineUmschalten(): void {
    this.filterSetzen({ ...this.filter, nurMeine: !this.filter.nurMeine });
  }

  verworfenUmschalten(): void {
    this.filterSetzen({ ...this.filter, verworfenSichtbar: !this.filter.verworfenSichtbar });
  }

  // Karten

  /**
   * Was der Griff auf einer Karte ausloest (``EinwurfAktionenService``). Nach dem
   * Verwerfen laedt die Liste neu: Der Einwurf verschwindet hinter dem Chip, und der
   * Zaehler oben muss das mitbekommen.
   */
  aktionAusfuehren(karte: KartenDaten, aktion: EinwurfAktion): void {
    this.einwurfAktionen
      .ausfuehren(karte, aktion)
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => this.laden());
  }

  nachKarte(_index: number, karte: KartenDaten): string {
    return karte.id;
  }

  /** Mit ?von=fangkorb: Der Pfeil auf /einwerfen fuehrt dann hierher zurueck (app.routes.ts). */
  zumEinwerfen(): void {
    this.router.navigate(['/einwerfen'], { queryParams: { von: 'fangkorb' } });
  }

  private fokusAmErneutKnopf(): boolean {
    return !!document.activeElement?.classList.contains('erneut-versuchen');
  }

  /** Der Knopf verschwindet mit dem Erfolg; der Fokus geht in den Bereich des Tabs. */
  private fokusInDieListe(): void {
    this.cdr.detectChanges();
    this.host.nativeElement.querySelector<HTMLElement>(`#fangkorb-bereich-${this.filter.tab}`)?.focus();
  }

  ngOnDestroy(): void {
    this.wiederholung.abbrechen();
    this.destroy$.next();
    this.destroy$.complete();
  }

  private filterSetzen(filter: FangkorbFilter): void {
    this.filter = filter;
    filterSpeichern(filter);
    this.filtern();
  }

  private filtern(): void {
    this.gefiltert = this.einwuerfe
      .filter((einwurf) => passtZumFilter(einwurf, this.filter))
      .sort((links, rechts) => this.alter(rechts) - this.alter(links));

    for (const tab of TABS) {
      this.zaehler[tab.wert] = this.gefiltert.filter((einwurf) =>
        passtZumTab(einwurf, tab.wert, this.filter.verworfenSichtbar),
      ).length;
    }

    this.sichtbar = this.gefiltert.filter((einwurf) =>
      passtZumTab(einwurf, this.filter.tab, this.filter.verworfenSichtbar),
    );
    this.karten = this.sichtbar.map(ausEinwurf);
    this.cdr.markForCheck();
  }

  /** Ein unlesbarer Zeitstempel sortiert nach hinten, statt die Liste zu wuerfeln. */
  private alter(einwurf: Einwurf): number {
    const millis = new Date(einwurf.created_at).getTime();
    return Number.isNaN(millis) ? 0 : millis;
  }
}
