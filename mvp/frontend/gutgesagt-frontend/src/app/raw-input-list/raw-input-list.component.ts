import {
  Component,
  OnInit,
  OnDestroy,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

import { EinwurfAktionenService } from './einwurf-aktionen.service';

import { Einwurf, EinwurfService } from '../services/einwurf.service';
import { AuthService } from '../auth/auth.service';
import { LoggingService } from '../services/logging.service';
import { Plattform, PLATTFORMEN } from '../shared/plattform';
import { FANGKORB_BESCHREIBUNG } from '../shared/fangkorb-texte';
import { BeitragskarteComponent } from '../beitragskarte/beitragskarte.component';
import { KartenDaten, EinwurfAktion, ausEinwurf } from '../beitragskarte/karten-daten';
import { HilfeUmschalterComponent } from '../shared/components/hilfe-umschalter/hilfe-umschalter.component';
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
 * Der Fangkorb: drei Tabs, benannt nach der naechsten Arbeit, in jedem die
 * Einwuerfe, an denen dort etwas zu tun ist.
 *
 * Destillieren = offen (noch kein Satz), Ausformulieren = destilliert (Saetze ohne
 * Beitrag), Ausformuliert = mit mindestens einem Beitrag verknuepft (neu oder
 * vorhanden). Verworfenes liegt unter Ausformuliert hinter einem Chip. Welche
 * Stufe gilt, entscheidet ``stufeVonEinwurf``, welcher Tab dazu gehoert
 * ``passtZumTab``; die Chips (Plattform, "nur meine") wirken quer dazu und gelten
 * auch fuer die Zaehler.
 *
 * Bewusst alle Einwuerfe und nicht nur die eigenen - der Vorrat ist gemeinsam.
 * Sortiert wird hier neueste zuerst, nicht in der Reihenfolge des Servers
 * (eigene zuerst): im Fangkorb zaehlt das Alter, nicht die Person.
 */
@Component({
  selector: 'app-raw-input-list',
  standalone: true,
  imports: [CommonModule, MatProgressSpinnerModule, MatButtonModule, MatIconModule, BeitragskarteComponent, HilfeUmschalterComponent],
  templateUrl: './raw-input-list.component.html',
  styleUrls: ['./raw-input-list.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RawInputListComponent implements OnInit, OnDestroy {
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
  zaehler: Record<FangkorbTab, number> = { destillieren: 0, ausformulieren: 0, ausformuliert: 0 };
  gesamt = 0;
  filter: FangkorbFilter = filterLaden();
  isLoading = true;
  ladefehler = false;

  /** Die angemeldete Person; die Karte nennt daran den Einwerfer oder eben nicht. */
  eigeneKennung: string | null = null;

  private destroy$ = new Subject<void>();

  constructor(
    private einwurfService: EinwurfService,
    private router: Router,
    private authService: AuthService,
    private logger: LoggingService,
    private cdr: ChangeDetectorRef,
    private einwurfAktionen: EinwurfAktionenService,
  ) {}

  ngOnInit(): void {
    this.eigeneKennung = this.authService.getCurrentUserId();
    if (!this.eigeneKennung) {
      this.authService
        .fetchUserInfo()
        .pipe(takeUntil(this.destroy$))
        .subscribe({
          next: (info) => {
            this.eigeneKennung = info?.userId ?? null;
            this.filtern();
          },
          error: () => (this.eigeneKennung = null),
        });
    }
    this.laden();
  }

  laden(): void {
    this.isLoading = true;
    this.ladefehler = false;
    this.einwurfService
      .fangkorbLaden(1, LADE_GROESSE)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (daten) => {
          this.einwuerfe = daten.results;
          this.gesamt = daten.total_records_count;
          this.isLoading = false;
          this.filtern();
        },
        error: (error) => {
          this.logger.error('Fangkorb konnte nicht geladen werden', error);
          this.isLoading = false;
          this.ladefehler = true;
          this.cdr.markForCheck();
        },
      });
  }

  // Tabs

  tabWaehlen(tab: FangkorbTab): void {
    this.filterSetzen({ ...this.filter, tab });
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
   * Verwerfen laedt die Liste neu: Der Einwurf wechselt den Tab, und der Zaehler
   * oben muss das mitbekommen.
   */
  aktionAusfuehren(karte: KartenDaten, aktion: EinwurfAktion): void {
    this.einwurfAktionen.ausfuehren(karte, aktion, () => this.laden(), this.destroy$);
  }

  nachKarte(_index: number, karte: KartenDaten): string {
    return karte.id;
  }

  /** Mit ?von=fangkorb: Der Pfeil auf /einwerfen fuehrt dann hierher zurueck (app.routes.ts). */
  zumEinwerfen(): void {
    this.router.navigate(['/einwerfen'], { queryParams: { von: 'fangkorb' } });
  }

  ngOnDestroy(): void {
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
      .filter((einwurf) => passtZumFilter(einwurf, this.filter, this.eigeneKennung))
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
