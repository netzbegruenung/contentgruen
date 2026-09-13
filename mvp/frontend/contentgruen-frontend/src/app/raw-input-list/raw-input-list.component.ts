import {
  Component,
  OnInit,
  OnDestroy,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

import {
  RawInput,
  RawInputDraft,
  RawInputService,
  RawInputStatus,
} from '../services/raw-input.service';
import { AuthService } from '../auth/auth.service';
import { LoggingService } from '../services/logging.service';
import { kurzeKennung } from '../shared/kennung';
import { Plattform, PLATTFORMEN, plattformAusUrl, plattformName } from '../shared/plattform';
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

/** Die vier Kartenzustaende. in_progress heisst im UI "destilliert". */
export type KartenZustand = 'offen' | 'destilliert' | 'ausformuliert' | 'verworfen';

const ZUSTAND: Record<RawInputStatus, KartenZustand> = {
  open: 'offen',
  in_progress: 'destilliert',
  processed: 'ausformuliert',
  discarded: 'verworfen',
};

/**
 * Der Fangkorb als Kartenliste: ein Strom, eigene zuerst, dann neueste (sortiert
 * der Server). Keine Gruppen - den Stand zeigt die Kartenoptik.
 *
 * Bewusst alle Einwuerfe und nicht nur die eigenen - der Vorrat ist gemeinsam.
 * Ein Tipp auf eine offene, destillierte oder verworfene Karte oeffnet den
 * Einwurf zum Destillieren; eine ausformulierte Karte fuehrt zum Beitrag.
 */
@Component({
  selector: 'app-raw-input-list',
  standalone: true,
  imports: [CommonModule, RouterLink, MatProgressSpinnerModule, MatButtonModule, MatIconModule],
  templateUrl: './raw-input-list.component.html',
  styleUrls: ['./raw-input-list.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RawInputListComponent implements OnInit, OnDestroy {
  readonly plattformen = PLATTFORMEN;
  readonly kurzeKennung = kurzeKennung;

  einwuerfe: RawInput[] = [];
  sichtbar: RawInput[] = [];
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

  // Filter

  plattformAktiv(plattform: Plattform): boolean {
    return this.filter.plattformen.includes(plattform);
  }

  plattformUmschalten(plattform: Plattform): void {
    const aktiv = this.plattformAktiv(plattform);
    const plattformen = PLATTFORMEN.map((eintrag) => eintrag.wert).filter((wert) =>
      wert === plattform ? !aktiv : this.plattformAktiv(wert),
    );
    this.filterSetzen({ ...this.filter, plattformen });
  }

  nurOffeneUmschalten(): void {
    this.filterSetzen({ ...this.filter, nurOffene: !this.filter.nurOffene });
  }

  nurMeineUmschalten(): void {
    this.filterSetzen({ ...this.filter, nurMeine: !this.filter.nurMeine });
  }

  // Karten

  zustand(einwurf: RawInput): KartenZustand {
    return ZUSTAND[einwurf.status] ?? 'offen';
  }

  kartenKlassen(einwurf: RawInput): string[] {
    const klassen = [`zustand-${this.zustand(einwurf)}`];
    if (this.zustand(einwurf) === 'ausformuliert') {
      klassen.push(`typ-${einwurf.links?.[0]?.content_type ?? 'unbekannt'}`);
    }
    return klassen;
  }

  kartenBeschriftung(einwurf: RawInput): string {
    const zustand = this.zustand(einwurf);
    return zustand === 'ausformuliert' && this.suchSatz(einwurf)
      ? 'Einwurf, ausformuliert: in der Suche anzeigen'
      : `Einwurf, ${zustand}: destillieren`;
  }

  plattformName(einwurf: RawInput): string | null {
    const plattform = plattformAusUrl(einwurf.url);
    return plattform ? plattformName(plattform) : null;
  }

  /** Der Hinweis fuer andere, sofern er mehr ist als der Link selbst. */
  hinweis(einwurf: RawInput): string | null {
    const inhalt = einwurf.content?.trim();
    return inhalt && inhalt !== einwurf.url ? inhalt : null;
  }

  /** Alle Saetze, je mit Person - fuer destillierte Karten. */
  alleSaetze(einwurf: RawInput): RawInputDraft[] {
    return einwurf.drafts ?? [];
  }

  /**
   * Die Saetze, aus denen ein Beitrag wurde. Fehlt die Zuordnung (Satz spaeter
   * geleert, Verknuepfung aus der Zeit vor v2), stehen alle vorhandenen Saetze da.
   */
  ausformulierteSaetze(einwurf: RawInput): RawInputDraft[] {
    const ids = new Set((einwurf.links ?? []).map((link) => link.draft_id).filter(Boolean));
    const saetze = this.alleSaetze(einwurf);
    const zugeordnet = saetze.filter((satz) => ids.has(satz.id));
    return zugeordnet.length ? zugeordnet : saetze;
  }

  /** Womit die ausformulierte Karte die Suche aufruft. */
  suchSatz(einwurf: RawInput): string | null {
    return this.ausformulierteSaetze(einwurf)[0]?.sentence ?? null;
  }

  oeffnen(einwurf: RawInput): void {
    const satz = this.zustand(einwurf) === 'ausformuliert' ? this.suchSatz(einwurf) : null;
    if (satz) {
      this.router.navigate(['/result'], { queryParams: { searchQuery: satz } });
      return;
    }
    this.router.navigate(['/destillieren', einwurf.id]);
  }

  nachId(_index: number, einwurf: RawInput): string {
    return einwurf.id;
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
    this.cdr.markForCheck();
  }
}
