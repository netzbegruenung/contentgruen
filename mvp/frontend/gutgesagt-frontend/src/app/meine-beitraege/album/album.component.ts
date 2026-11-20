import {
  AfterViewInit,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  ElementRef,
  EventEmitter,
  Input,
  NgZone,
  OnChanges,
  OnDestroy,
  Output,
  ViewChild,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { BreakpointObserver } from '@angular/cdk/layout';
import { MatIconModule } from '@angular/material/icon';
import { Subject, Subscription } from 'rxjs';
import { debounceTime } from 'rxjs/operators';

import { BeitragskarteComponent } from '../../beitragskarte/beitragskarte.component';
import { KartenDaten } from '../../beitragskarte/karten-daten';
import { Meilenstein } from '../../services/usage-tracking.service';
import { Stil } from '../../shared/zweck-stil';
import { wirkungssatz } from '../wirkung';
import {
  ABSCHNITTE_AB,
  AlbumAbschnitt,
  AlbumEintrag,
  AlbumFilter,
  AlbumKennzahlen,
  Auswahl,
  KARTEN_JE_ABSCHNITT,
  KEIN_FILTER,
  SUCHE_AB,
  abschnittStand,
  beitraegeInThemen,
  abschnitte,
  filterAktiv,
  filtern,
  kennzahlen,
  nachNutzung,
  stilAuswahl,
  themenAuswahl,
} from './album';

/** Wartezeit nach dem letzten Tastendruck, bevor die Suche filtert. */
export const SUCHE_WARTEN_MS = 150;

/**
 * Das Album in „Meine Beiträge“ (Variante A „Album nach Thema“, Sebastian und Aila 20.11.).
 *
 * Oben der Deckel mit drei Zahlen und dem Wirkungssatz. Ohne jede Nutzung steht statt
 * „0× genutzt“ der nächste Meilenstein groß mit Balken, ohne Meilensteine (Punkte aus
 * oder keine Einwilligung) groß „244 Beiträge in 12 Themen“ (Entscheidungen 20.11.).
 *
 * Darunter eine klebende Suche über die eigenen Beiträge mit Filtern Thema, Stil und
 * „genutzt“ und der Trefferzahl. Sie läuft im Browser: Die Seite lädt ohnehin alle
 * eigenen Beiträge, weil Abschnitte, Zahlen und Fortschritt alle brauchen, und 300
 * Einträge zu durchsuchen kostet weniger als ein Abruf je Tastendruck. Am Handy klappen
 * Thema, Stil und „genutzt“ in einen Knopf „Filter“ ein, sobald die Leiste oben klebt;
 * das Suchfeld bleibt. Bis SUCHE_AB - 1 Beiträge gibt es weder Suche noch Filter.
 *
 * Dann die Abschnitte je Thema (album.ts), einklappbar, mit „5 von 25 genutzt“. Nur der
 * erste ist anfangs offen, ein offener zeigt zuerst KARTEN_JE_ABSCHNITT Karten: Bei 244
 * Beiträgen stehen so anfangs höchstens sechs volle Karten im DOM, zugeklappte
 * Abschnitte zeichnen keine. Bis ABSCHNITTE_AB - 1 Beiträge stehen die Karten ohne
 * Abschnitte untereinander.
 *
 * Die Karten sind die volle Beitragskarte der Ergebnisseite im eigenen Album-Modus
 * (Ändern, Teilen, ⋮); was „Ändern“ und „Löschen“ auslösen, macht die Seite.
 */
@Component({
  selector: 'app-album',
  standalone: true,
  imports: [CommonModule, MatIconModule, BeitragskarteComponent],
  templateUrl: './album.component.html',
  styleUrls: ['./album.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AlbumComponent implements OnChanges, AfterViewInit, OnDestroy {
  @Input() eintraege: AlbumEintrag[] = [];
  /** Der nächste offene Meilenstein; null ohne Meilensteine (keine Einwilligung, Punkte aus). */
  @Input() naechsterMeilenstein: Meilenstein | null = null;

  @Output() aendern = new EventEmitter<KartenDaten>();
  @Output() loeschen = new EventEmitter<KartenDaten>();

  readonly KARTEN_JE_ABSCHNITT = KARTEN_JE_ABSCHNITT;

  filter: AlbumFilter = { ...KEIN_FILTER };
  zahlen: AlbumKennzahlen = kennzahlen([]);
  liste: AlbumAbschnitt[] = [];
  /** Ohne Abschnitte (wenige Beiträge): die Karten untereinander. */
  flach: AlbumEintrag[] = [];
  treffer = 0;
  themen: Auswahl<string>[] = [];
  stile: Auswahl<Stil>[] = [];

  /** Vom Nutzer auf- oder zugeklappt; sonst ist nur der erste Abschnitt offen. */
  private umgeschaltet = new Map<string, boolean>();
  /** Abschnitte, die schon alle Karten zeigen. */
  private alleGezeigt = new Set<string>();

  /** Die Suchleiste klebt oben (die Marke davor ist aus dem Bild). */
  klebt = false;
  istMobil = false;
  /** Am Handy, wenn die Leiste klebt: Filter über den Knopf „Filter“ aufgeklappt. */
  filterOffen = false;

  @ViewChild('marke') private marke?: ElementRef<HTMLElement>;
  @ViewChild('suchfeld') private suchfeld?: ElementRef<HTMLInputElement>;
  /** Nach „Beitrag löschen“: wo der Fokus hin soll, sobald die Liste ohne ihn kommt. */
  private fokusNachLoeschen: { id: string; folgende: string[]; abschnitt: string | null } | null = null;
  private beobachter?: IntersectionObserver;
  private readonly suche$ = new Subject<string>();
  private readonly abos = new Subscription();

  constructor(
    private cdr: ChangeDetectorRef,
    private zone: NgZone,
    private host: ElementRef<HTMLElement>,
    breakpoints: BreakpointObserver,
  ) {
    this.abos.add(
      this.suche$.pipe(debounceTime(SUCHE_WARTEN_MS)).subscribe((suche) => {
        this.filterSetzen({ ...this.filter, suche });
      }),
    );
    this.abos.add(
      breakpoints.observe('(max-width: 599px)').subscribe((zustand) => {
        this.istMobil = zustand.matches;
        this.cdr.markForCheck();
      }),
    );
  }

  ngOnChanges(): void {
    this.neuRechnen();
    this.fokusNachdemGeloescht();
  }

  ngAfterViewInit(): void {
    if (typeof IntersectionObserver === 'undefined') {
      return;
    }
    // Ausserhalb der Zone: Scrollen soll keine Pruefung der ganzen Seite ausloesen.
    this.zone.runOutsideAngular(() => {
      this.beobachter = new IntersectionObserver(([eintrag]) => {
        const klebt = !eintrag.isIntersecting && eintrag.boundingClientRect.top < 0;
        if (klebt !== this.klebt) {
          this.zone.run(() => {
            this.klebt = klebt;
            if (!klebt) {
              this.filterOffen = false;
            }
            this.cdr.markForCheck();
          });
        }
      });
      if (this.marke) {
        this.beobachter.observe(this.marke.nativeElement);
      }
    });
  }

  ngOnDestroy(): void {
    this.beobachter?.disconnect();
    this.abos.unsubscribe();
  }

  get mitSuche(): boolean {
    return this.eintraege.length >= SUCHE_AB;
  }

  get mitAbschnitten(): boolean {
    return this.eintraege.length >= ABSCHNITTE_AB;
  }

  get aktiv(): boolean {
    return filterAktiv(this.filter);
  }

  /** Am Handy, sobald die Leiste klebt: nur Suchfeld und Knopf „Filter“. */
  get filterEingeklappt(): boolean {
    return this.istMobil && this.klebt && !this.filterOffen;
  }

  /** Wie viele der Filter Thema, Stil, „genutzt“ gesetzt sind (am Knopf „Filter“). */
  get gesetzteFilter(): number {
    return [this.filter.thema !== null, this.filter.stil !== null, this.filter.nurGenutzt].filter((x) => x).length;
  }

  get suchName(): string {
    return `In deinen ${this.eintraege.length} Beiträgen suchen`;
  }

  get trefferText(): string {
    const gesamt = this.eintraege.length;
    if (this.aktiv) {
      return `${this.treffer} von ${gesamt} ${gesamt === 1 ? 'Beitrag' : 'Beiträgen'}`;
    }
    return `${gesamt} Beiträge · nach Thema, meistgenutzte zuerst`;
  }

  get wirkung(): string {
    return wirkungssatz(this.zahlen.beitraege, this.zahlen.nutzung, this.zahlen.dieseWoche);
  }

  /** Ohne jede Nutzung: der nächste Meilenstein groß statt „0× genutzt“ (Entscheidung 20.11.). */
  get meilensteinGross(): boolean {
    return this.zahlen.nutzung === 0 && this.naechsterMeilenstein !== null;
  }

  /**
   * Ohne Nutzung und ohne Meilenstein (Punkte aus oder keine Einwilligung): statt der drei
   * Zahlen mit „0× genutzt“ groß „244 Beiträge in 12 Themen“ (Entscheidung 20.11.).
   */
  get beitraegeGross(): boolean {
    return this.zahlen.nutzung === 0 && this.naechsterMeilenstein === null;
  }

  get beitraegeSatz(): string {
    return beitraegeInThemen(this.zahlen);
  }

  get meilensteinProzent(): number {
    const m = this.naechsterMeilenstein;
    return m && m.schwelle > 0 ? Math.min(100, Math.round((m.stand / m.schwelle) * 100)) : 0;
  }

  get meilensteinRest(): number {
    const m = this.naechsterMeilenstein;
    return m ? Math.max(0, m.schwelle - m.stand) : 0;
  }

  // Filter

  sucheGetippt(wert: string): void {
    this.suche$.next(wert);
  }

  sucheLeeren(): void {
    this.filterSetzen({ ...this.filter, suche: '' });
    this.suchfeldLeeren();
  }

  themaGewaehlt(wert: string): void {
    this.filterSetzen({ ...this.filter, thema: wert || null });
  }

  stilGewaehlt(wert: string): void {
    this.filterSetzen({ ...this.filter, stil: (wert || null) as Stil | null });
  }

  genutztUmschalten(): void {
    this.filterSetzen({ ...this.filter, nurGenutzt: !this.filter.nurGenutzt });
  }

  /** Alles zuruecksetzen, auch den Text im Suchfeld; der Fokus geht ins Suchfeld. */
  zuruecksetzen(): void {
    this.filterSetzen({ ...KEIN_FILTER });
    this.suchfeldLeeren();
  }

  /** Ein neuer Filter oeffnet die Abschnitte neu: Was unter dem alten auf- oder zugeklappt war, gilt nicht mehr. */
  private filterSetzen(filter: AlbumFilter): void {
    this.filter = filter;
    this.umgeschaltet.clear();
    this.neuRechnen();
  }

  private suchfeldLeeren(): void {
    this.cdr.detectChanges();
    const feld = this.suchfeld?.nativeElement;
    if (feld) {
      feld.value = '';
      feld.focus();
    }
  }

  filterUmschalten(): void {
    this.filterOffen = !this.filterOffen;
  }

  // Abschnitte

  /** Mit Filter sind anfangs alle Abschnitte mit Treffern offen, sonst der erste; was jemand umschaltet, gilt. */
  offen(abschnitt: AlbumAbschnitt, index: number): boolean {
    return this.umgeschaltet.get(abschnitt.thema.schluessel) ?? (this.aktiv || index === 0);
  }

  umschalten(abschnitt: AlbumAbschnitt, index: number): void {
    this.umgeschaltet.set(abschnitt.thema.schluessel, !this.offen(abschnitt, index));
  }

  sichtbare(abschnitt: AlbumAbschnitt): AlbumEintrag[] {
    const alle =
      this.alleGezeigt.has(abschnitt.thema.schluessel) || abschnitt.eintraege.length <= KARTEN_JE_ABSCHNITT + 2;
    return alle ? abschnitt.eintraege : abschnitt.eintraege.slice(0, KARTEN_JE_ABSCHNITT);
  }

  /** Alle Karten zeigen; der Fokus geht auf die erste neue, der Knopf verschwindet ja. */
  alleZeigen(abschnitt: AlbumAbschnitt): void {
    this.alleGezeigt.add(abschnitt.thema.schluessel);
    this.cdr.detectChanges();
    const liste = this.host.nativeElement.querySelector<HTMLElement>(`#album-${abschnitt.thema.schluessel}`);
    liste?.querySelectorAll<HTMLElement>('.platz')[KARTEN_JE_ABSCHNITT]?.focus();
  }

  /**
   * „Beitrag löschen“ an einer Karte: an die Seite melden und vormerken, wohin der Fokus
   * geht, wenn die Karte verschwindet (sonst fiele er auf die Seite, 2.4.3): auf die naechste
   * Karte im selben Abschnitt, sonst die vorige, sonst den Abschnittskopf.
   */
  loeschenAngetippt(karte: KartenDaten): void {
    const platz = this.host.nativeElement.querySelector<HTMLElement>(`.platz[data-id="${CSS.escape(karte.id)}"]`);
    const liste = platz?.parentElement;
    const plaetze = liste ? Array.from(liste.querySelectorAll<HTMLElement>(':scope > .platz')) : [];
    const index = platz ? plaetze.indexOf(platz) : -1;
    const folgende = [...plaetze.slice(index + 1), ...plaetze.slice(0, Math.max(index, 0)).reverse()]
      .map((p) => p.dataset['id'] ?? '')
      .filter((id) => !!id);
    const abschnitt = platz?.closest<HTMLElement>('.abschnitt')?.dataset['thema'] ?? null;
    this.fokusNachLoeschen = { id: karte.id, folgende, abschnitt };
    // Der Abschnitt bleibt offen, auch wenn er nach dem Loeschen weiter unten einsortiert wird.
    if (abschnitt) {
      this.umgeschaltet.set(abschnitt, true);
    }
    this.loeschen.emit(karte);
  }

  private fokusNachdemGeloescht(): void {
    const ziel = this.fokusNachLoeschen;
    if (!ziel || this.eintraege.some((e) => e.karte.id === ziel.id)) {
      return;
    }
    this.fokusNachLoeschen = null;
    // Erst nach dem Zeichnen der neuen Liste, sonst sitzt der Fokus auf einem Element, das gleich ersetzt wird.
    setTimeout(() => this.fokusSetzen(ziel));
  }

  private fokusSetzen(ziel: { folgende: string[]; abschnitt: string | null }): void {
    const wurzel = this.host.nativeElement;
    for (const id of ziel.folgende) {
      const platz = wurzel.querySelector<HTMLElement>(`.platz[data-id="${CSS.escape(id)}"]`);
      if (platz) {
        platz.focus();
        return;
      }
    }
    const kopf = ziel.abschnitt
      ? wurzel.querySelector<HTMLElement>(`.abschnitt[data-thema="${CSS.escape(ziel.abschnitt)}"] .abschnitt-knopf`)
      : null;
    (kopf ?? wurzel.querySelector<HTMLElement>('.abschnitt-knopf, input[type="search"]'))?.focus();
  }

  stand(abschnitt: AlbumAbschnitt): string {
    return abschnittStand(abschnitt);
  }

  prozent(abschnitt: AlbumAbschnitt): number {
    return Math.round((abschnitt.genutzt / abschnitt.eintraege.length) * 100);
  }

  nachSchluessel(_index: number, abschnitt: AlbumAbschnitt): string {
    return abschnitt.thema.schluessel;
  }

  nachId(_index: number, eintrag: AlbumEintrag): string {
    return eintrag.karte.id;
  }

  private neuRechnen(): void {
    // Unter SUCHE_AB gibt es keine Suchleiste und damit keinen Weg zurueck: dann auch keinen Filter.
    if (!this.mitSuche && filterAktiv(this.filter)) {
      this.filter = { ...KEIN_FILTER };
      this.umgeschaltet.clear();
    }
    this.zahlen = kennzahlen(this.eintraege);
    this.themen = themenAuswahl(this.eintraege);
    this.stile = stilAuswahl(this.eintraege);
    // Ein Filter auf ein Thema oder einen Stil, den es nach dem Loeschen nicht mehr gibt, faellt weg.
    if (this.filter.thema !== null && !this.themen.some((t) => t.wert === this.filter.thema)) {
      this.filter = { ...this.filter, thema: null };
    }
    if (this.filter.stil !== null && !this.stile.some((s) => s.wert === this.filter.stil)) {
      this.filter = { ...this.filter, stil: null };
    }
    const gefiltert = filtern(this.eintraege, this.filter);
    this.treffer = gefiltert.length;
    this.liste = this.mitAbschnitten ? abschnitte(gefiltert) : [];
    this.flach = this.mitAbschnitten ? [] : nachNutzung(gefiltert);
    this.cdr.markForCheck();
  }
}
