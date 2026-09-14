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

import { RawInput, RawInputService } from '../services/raw-input.service';
import { AuthService } from '../auth/auth.service';
import { LoggingService } from '../services/logging.service';
import { Plattform, PLATTFORMEN } from '../shared/plattform';
import { FANGKORB_BESCHREIBUNG, KETTEN_ICONS } from '../shared/fangkorb-texte';
import { BeitragskarteComponent } from '../beitragskarte/beitragskarte.component';
import { KartenDaten, ausEinwurf } from '../beitragskarte/karten-daten';
import {
  FangkorbFilter,
  filterLaden,
  filterSpeichern,
  passtZumFilter,
} from './fangkorb-filter';

/**
 * So viele Einwuerfe laedt der Fangkorb auf einmal - mehr gibt der Endpunkt je
 * Seite nicht her. Gefiltert wird im Browser; liegen mehr im Fangkorb, sagt die
 * Liste das dazu.
 */
export const LADE_GROESSE = 100;

/** Ein Einwurf als Stapel: oben die Einwurf-Karte, darunter je Satz eine Karte. */
export interface Stapel {
  id: string;
  einwurf: KartenDaten;
  saetze: KartenDaten[];
}

/**
 * Der Fangkorb als Liste von Stapeln: ein Strom, eigene zuerst, dann neueste
 * (sortiert der Server). Keine Gruppen - den Stand zeigt die Kartenoptik.
 *
 * Der Einwurf ist Rohmaterial, die Saetze sind die Rohlinge: Aus einem Einwurf koennen
 * mehrere Saetze und daraus verschiedene Beitraege werden. Den Zustand je Satz leitet
 * ausEinwurf aus den Verknuepfungen ab; der Status des Einwurfs steuert nur den Filter.
 *
 * Bewusst alle Einwuerfe und nicht nur die eigenen - der Vorrat ist gemeinsam.
 * Ein Tipp auf Einwurf oder Satz oeffnet den Einwurf zum Destillieren, auch mit
 * vorhandenen Saetzen: fuer einen weiteren Satz. Verworfenes ist nicht antippbar.
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
  readonly fangkorbBeschreibung = FANGKORB_BESCHREIBUNG;
  readonly kettenIcons = KETTEN_ICONS;

  /** Die Langfassung hinter dem Hilfe-Icon; zu, bis jemand danach fragt. */
  erklaerungOffen = false;
  einwuerfe: RawInput[] = [];
  sichtbar: RawInput[] = [];
  /** Die sichtbaren Einwuerfe als Karten, einmal je Filterlauf berechnet. */
  stapel: Stapel[] = [];
  gesamt = 0;
  filter: FangkorbFilter = filterLaden();
  isLoading = true;
  ladefehler = false;

  private eigeneKennung: string | null = null;
  private destroy$ = new Subject<void>();

  constructor(
    private rawInputService: RawInputService,
    private router: Router,
    private authService: AuthService,
    private logger: LoggingService,
    private cdr: ChangeDetectorRef,
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
   * Chips aus wie "nur offene" im Ruhezustand.
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

  nurOffeneUmschalten(): void {
    this.filterSetzen({ ...this.filter, nurOffene: !this.filter.nurOffene });
  }

  nurMeineUmschalten(): void {
    this.filterSetzen({ ...this.filter, nurMeine: !this.filter.nurMeine });
  }

  // Karten

  /** Einwurf und Satz fuehren beide zum Destillieren dieses Einwurfs. */
  oeffnen(karte: KartenDaten): void {
    if (!karte.rohling?.antippbar) {
      return;
    }
    this.router.navigate(['/destillieren', karte.rohling.einwurfId]);
  }

  inSucheAnzeigen(satz: string): void {
    this.router.navigate(['/result'], { queryParams: { searchQuery: satz } });
  }

  nachStapel(_index: number, eintrag: Stapel): string {
    return eintrag.id;
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
    this.sichtbar = this.einwuerfe.filter((einwurf) =>
      passtZumFilter(einwurf, this.filter, this.eigeneKennung),
    );
    this.stapel = this.sichtbar.map((einwurf) => {
      const [karte, ...saetze] = ausEinwurf(einwurf);
      return { id: einwurf.id, einwurf: karte, saetze };
    });
    this.cdr.markForCheck();
  }
}
