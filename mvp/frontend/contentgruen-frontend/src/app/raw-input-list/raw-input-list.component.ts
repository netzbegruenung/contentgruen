import {
  Component,
  OnInit,
  OnDestroy,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { Clipboard } from '@angular/cdk/clipboard';
import { MatBottomSheet } from '@angular/material/bottom-sheet';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

import { EinwurfBeitragSheetComponent } from './einwurf-beitrag-sheet.component';

import { RawInput, RawInputService } from '../services/raw-input.service';
import { AuthService } from '../auth/auth.service';
import { LoggingService } from '../services/logging.service';
import { Plattform, PLATTFORMEN } from '../shared/plattform';
import { FANGKORB_BESCHREIBUNG } from '../shared/fangkorb-texte';
import { BeitragskarteComponent } from '../beitragskarte/beitragskarte.component';
import { KartenDaten, RohlingAktion, ausEinwurf } from '../beitragskarte/karten-daten';
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
 * Der Fangkorb als Arbeitsvorrat: drei Tabs entlang der Arbeitsstufen, in jedem
 * die Rohlinge, an denen dort etwas zu tun ist.
 *
 * Destillieren = noch kein Satz, Ausformulieren = Saetze ohne Beitrag, Erledigt =
 * mindestens ein Beitrag entstanden. Verworfenes liegt unter Erledigt hinter
 * einem Chip. Welcher Zustand gilt, entscheidet ``zustandVonEinwurf``; die Chips
 * (Plattform, "nur meine") wirken quer dazu und gelten auch fuer die Zaehler.
 *
 * Bewusst alle Einwuerfe und nicht nur die eigenen - der Vorrat ist gemeinsam.
 * Sortiert wird hier neueste zuerst, nicht in der Reihenfolge des Servers
 * (eigene zuerst): im Arbeitsvorrat zaehlt das Alter, nicht die Person.
 */
@Component({
  selector: 'app-raw-input-list',
  standalone: true,
  imports: [CommonModule, MatProgressSpinnerModule, MatButtonModule, MatIconModule, BeitragskarteComponent],
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
  einwuerfe: RawInput[] = [];
  /** Was die Chips uebrig lassen, neueste zuerst - die Grundlage der Zaehler. */
  gefiltert: RawInput[] = [];
  sichtbar: RawInput[] = [];
  /** Die sichtbaren Einwuerfe als Karten, einmal je Filterlauf berechnet. */
  karten: KartenDaten[] = [];
  zaehler: Record<FangkorbTab, number> = { destillieren: 0, ausformulieren: 0, erledigt: 0 };
  gesamt = 0;
  filter: FangkorbFilter = filterLaden();
  isLoading = true;
  ladefehler = false;

  /** Die angemeldete Person; die Karte nennt daran den Einwerfer oder eben nicht. */
  eigeneKennung: string | null = null;

  private destroy$ = new Subject<void>();

  constructor(
    private rawInputService: RawInputService,
    private router: Router,
    private authService: AuthService,
    private logger: LoggingService,
    private cdr: ChangeDetectorRef,
    private bottomSheet: MatBottomSheet,
    private clipboard: Clipboard,
    private snackBar: MatSnackBar,
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
    this.rawInputService
      .getRawInputs(1, LADE_GROESSE)
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

  // Kopf

  erklaerungUmschalten(): void {
    this.erklaerungOffen = !this.erklaerungOffen;
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
   * Was der Griff auf einer Karte ausloest.
   *
   * Destillieren und Ausformulieren fuehren beide in die Destillier-Ansicht: Dort
   * steht der eigene Satz schon im Feld, und "Weiter" fuehrt zur Typwahl. Ein
   * eigenes Formular mit fremdem Satz gibt es nicht.
   */
  aktionAusfuehren(karte: KartenDaten, aktion: RohlingAktion): void {
    const rohling = karte.rohling;
    if (!rohling) {
      return;
    }
    switch (aktion) {
      case 'destillieren':
      case 'ausformulieren':
      case 'weiterDestillieren':
        this.router.navigate(['/destillieren', rohling.einwurfId]);
        break;
      case 'ansehen':
        this.bottomSheet.open(EinwurfBeitragSheetComponent, {
          data: { beitraege: rohling.beitraege },
          ariaLabel: karte.titel || 'Beitrag aus diesem Einwurf',
        });
        break;
      case 'linkKopieren':
        this.linkKopieren(rohling.link);
        break;
      case 'verwerfen':
        this.verwerfen(rohling.einwurfId);
        break;
    }
  }

  private linkKopieren(link: string | null): void {
    if (!link) {
      return;
    }
    const kopiert = this.clipboard.copy(link);
    this.snackBar.open(kopiert ? 'Link kopiert.' : 'Kopieren hat nicht geklappt.', undefined, {
      duration: 3000,
    });
  }

  /**
   * Verwerfen und die Liste neu laden: Der Einwurf wechselt damit den Tab, und der
   * Zaehler oben muss das mitbekommen.
   */
  private verwerfen(einwurfId: string): void {
    this.rawInputService
      .updateStatus(einwurfId, 'discarded')
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.snackBar.open('Verworfen.', undefined, { duration: 3000 });
          this.laden();
        },
        error: (error) => {
          this.logger.error('Einwurf konnte nicht verworfen werden', error);
          this.snackBar.open(
            error?.status === 403
              ? 'Verwerfen kann nur, wer den Einwurf eingeworfen hat.'
              : 'Verwerfen hat nicht geklappt. Bitte versuche es erneut.',
            'OK',
            { duration: 6000 },
          );
        },
      });
  }

  nachKarte(_index: number, karte: KartenDaten): string {
    return karte.id;
  }

  zumEinwerfen(): void {
    this.router.navigate(['/einwerfen']);
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
  private alter(einwurf: RawInput): number {
    const millis = new Date(einwurf.created_at).getTime();
    return Number.isNaN(millis) ? 0 : millis;
  }
}
