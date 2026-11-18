import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, ActivatedRoute, RouterLink } from '@angular/router';
import { ROUTES } from '../shared/constants/app.constants';
import { Subscription, Observable, Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { SearchService } from '../services/search.service';
import { SearchResponse } from '../services/dtos/searchDtos';
import { KartenlisteComponent } from '../beitragskarte/kartenliste.component';
import { SearchComponent } from '../search/search.component';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { ZuDieserAntwortComponent } from './zu-dieser-antwort.component';
import { StateManagementService } from '../services/state-management.service';
import { LoadingSpinnerComponent } from '../shared/components/loading-spinner/loading-spinner.component';
import { ErrorMessageComponent } from '../shared/components/error-message/error-message.component';
import { BreakpointObserver } from '@angular/cdk/layout';
import { FORMULAR_PFAD, aussageParameterMitText, istAussageId } from '../shared/formular-adresse';
import { BaseSearchResult } from '../services/dtos/commonDtos';
import { Thema } from '../services/dtos/themenDtos';
import { ThemenFilterComponent } from '../shared/themen/themen-filter.component';
import { NichtDabeiComponent } from '../nicht-dabei/nicht-dabei.component';
import { OftGesuchtComponent } from '../oft-gesucht/oft-gesucht.component';
import { KartenDaten, KartenKennzahlen, ausSuchergebnis } from '../beitragskarte/karten-daten';
import { StatementSearchResult } from '../services/dtos/statementDtos';
import { TeilenService, sucheLink, suchtextKuerzen } from '../shared/teilen.service';
import {
  AnsichtGruppe,
  ErgebnisGruppe,
  TREFFER_TYPEN,
  TrefferTyp,
  alleTreffer,
  ansichtBauen,
  mitZweiterSpalte,
  anzahlJeTyp,
  anzahlSichtbar,
  besteHervorheben,
  istWeniger,
  aufklappSchluessel,
  aussageSchluessel,
  gruppieren,
} from './ergebnis-gruppen';

/** Wie viele aehnliche Aussagen die Zeile "Erkannt als" unter "Nicht gemeint?" anbietet. */
const ALTERNATIVEN_ERKANNT = 3;

/** Ob ein Treffer zum Themenfilter passt; ohne Filter passt jeder. */
function passtZuThema(treffer: BaseSearchResult, thema: string | null): boolean {
  return thema === null || (treffer.themen ?? []).some((t) => t.schluessel === thema);
}

/**
 * Die Themen der Treffer, jedes einmal, in der Reihenfolge ihres ersten Auftretens.
 * Nur sie stehen im Filter: Ein Thema ohne Treffer liesse die Seite leer. Mit
 * ``nurAussage`` (Schluessel der erkannten Aussage) nur die Themen ihrer Treffer: Ein
 * Thema nur eingeklappter Treffer liesse die erkannte Gruppe wegfallen und die
 * weniger passenden offen dastehen.
 */
export function themenDerTreffer(antwort: SearchResponse, nurAussage: string | null = null): Thema[] {
  const gesehen = new Map<string, Thema>();
  const auswahl = alleTreffer(antwort).filter((t) => nurAussage === null || aussageSchluessel(t) === nurAussage);
  for (const treffer of auswahl) {
    for (const thema of treffer.themen ?? []) {
      if (!gesehen.has(thema.schluessel)) {
        gesehen.set(thema.schluessel, thema);
      }
    }
  }
  return [...gesehen.values()];
}

/** Die Aussage, als die die Suche verstanden wurde: ID (falls bekannt) und Text. */
export interface ErkannteAussage {
  id: string | null;
  text: string;
}

/**
 * Die erkannte Aussage (#642, R40): die Aussage, ueber die die meisten Treffer
 * gefunden wurden; bei Gleichstand die des Treffers mit dem hoechsten Score. Sie
 * steht im Kopfband ueber den Treffern, ihre Gruppe kommt zuerst. null, wenn kein
 * Treffer ueber eine Aussage kam (nur direkte Treffer) oder die gewaehlte weder den
 * obersten Treffer noch die Mehrheit traegt.
 */
export function erkannteAussage(antwort: SearchResponse): ErkannteAussage | null {
  const je = new Map<string, { aussage: ErkannteAussage; anzahl: number; bester: number }>();
  for (const treffer of alleTreffer(antwort)) {
    const schluessel = aussageSchluessel(treffer);
    if (!schluessel) {
      continue;
    }
    const eintrag = je.get(schluessel);
    if (eintrag) {
      eintrag.anzahl += 1;
      eintrag.bester = Math.max(eintrag.bester, treffer.score ?? 0);
    } else {
      je.set(schluessel, {
        aussage: { id: treffer.statement_id || null, text: treffer.statement_text!.trim() },
        anzahl: 1,
        bester: treffer.score ?? 0,
      });
    }
  }
  let gewaehlt: { aussage: ErkannteAussage; anzahl: number; bester: number } | null = null;
  let mitAussage = 0;
  let hoechster = -Infinity;
  for (const eintrag of je.values()) {
    mitAussage += eintrag.anzahl;
    hoechster = Math.max(hoechster, eintrag.bester);
  }
  for (const eintrag of je.values()) {
    if (
      !gewaehlt ||
      eintrag.anzahl > gewaehlt.anzahl ||
      (eintrag.anzahl === gewaehlt.anzahl && eintrag.bester > gewaehlt.bester)
    ) {
      gewaehlt = eintrag;
    }
  }
  // Nur, wenn das Kopfband fuer die Treffer steht: Die Aussage traegt den obersten
  // Treffer oder die Mehrheit. Verteilt auf viele Aussagen sagte es zu wenig.
  if (!gewaehlt || (gewaehlt.bester < hoechster && gewaehlt.anzahl * 2 <= mitAussage)) {
    return null;
  }
  return gewaehlt.aussage;
}

/** Der Gruppenschluessel der erkannten Aussage (wie aussageSchluessel); null ohne. */
export function erkannterSchluessel(erkannt: ErkannteAussage | null): string | null {
  return erkannt ? erkannt.id || `text:${erkannt.text}` : null;
}

/** Die Suchantwort mit nur den Treffern zum Thema, Zaehler passend dazu. */
export function nachThemaGefiltert(antwort: SearchResponse, thema: string | null): SearchResponse {
  if (thema === null) {
    return antwort;
  }
  const kommentare = (antwort.commentary_search_results ?? []).filter((t) => passtZuThema(t, thema));
  const hintergrund = (antwort.generictext_search_results ?? []).filter((t) => passtZuThema(t, thema));
  const posts = (antwort.post_search_results ?? []).filter((t) => passtZuThema(t, thema));
  const bilder = (antwort.image_search_results ?? []).filter((t) => passtZuThema(t, thema));
  return {
    ...antwort,
    commentary_search_results: kommentare,
    commentary_search_results_count: kommentare.length,
    generictext_search_results: hintergrund,
    generictext_search_results_count: hintergrund.length,
    post_search_results: posts,
    post_search_results_count: posts.length,
    image_search_results: bilder,
    image_search_results_count: bilder.length,
  };
}

@Component({
  selector: 'app-result-view',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    RouterLink,
    KartenlisteComponent,
    SearchComponent,
    MatButtonModule,
    MatIconModule,
    ZuDieserAntwortComponent,
    LoadingSpinnerComponent,
    ErrorMessageComponent,
    ThemenFilterComponent,
    NichtDabeiComponent,
    OftGesuchtComponent
  ],
  templateUrl: './result-view.component.html',
  styleUrls: ['./result-view.component.css'],
})
export class ResultViewComponent implements OnInit, OnDestroy {
  searchQuery$: Observable<string>;
  searchResponse$: Observable<SearchResponse | null>;
  loading$: Observable<boolean>;
  error$: Observable<string | null>;

  searchQuery: string = '';
  private queryParamsSubscription?: Subscription;
  private destroy$ = new Subject<void>();

  isMobile: boolean = false;

  // Themenfilter: die Themen der Aussagen, ueber die die Treffer gefunden wurden.
  // `angezeigt` ist die Suchantwort mit nur den Treffern zum aktiven Thema.
  private antwort: SearchResponse | null = null;
  angezeigt: SearchResponse | null = null;
  themenDerTreffer: Thema[] = [];
  aktivesThema: string | null = null;
  bekannteAussagen: string[] = [];
  /** In der Zeile "Erkannt als" (#642, V3); aus allen Treffern, nicht nur denen zum Thema. */
  erkannt: ErkannteAussage | null = null;

  // Einmal je Suchantwort und Wahl umgerechnet, nicht im Template: neue Objekte bei
  // jeder Change Detection setzten die Karten zurueck (Kurz/Lang, Aufklapper).
  private gruppen: ErgebnisGruppe[] = [];
  /**
   * Karten je Treffer, einmal je Suchantwort gebaut: Der Themenfilter gruppiert neu,
   * die Karten bleiben dieselben Objekte, und die Beitragskarte setzt Fassung,
   * Aufklapper und Nutzung nicht zurueck (ngOnChanges bei neuen Daten).
   */
  private karten = new WeakMap<BaseSearchResult, KartenDaten>();
  private readonly karteZu = (treffer: BaseSearchResult): KartenDaten => {
    let karte = this.karten.get(treffer);
    if (!karte) {
      karte = ausSuchergebnis(treffer);
      this.karten.set(treffer, karte);
    }
    return karte;
  };
  ansicht: AnsichtGruppe[] = [];
  /** Treffer je Typ, die ohne Aufklappen dastehen. */
  anzahl: Record<TrefferTyp, number> = anzahlJeTyp(null);
  /** Alle Treffer je Typ, auch die weniger passenden: fuer den Leerzustand. */
  private anzahlAlle: Record<TrefferTyp, number> = anzahlJeTyp(null);
  /** Gruppen, die ohne Aufklappen dastehen, und die weniger passenden darunter. */
  hauptGruppen: AnsichtGruppe[] = [];
  weitereGruppen: AnsichtGruppe[] = [];
  weitereAnzahl = 0;
  /**
   * Am Desktop zwei Spalten (Maintainer 18.11.): oben die beste Antwort und "Zu dieser Antwort",
   * darunter die weiteren Karten zu zweit. Immer, wenn es eine beste Antwort gibt; die Spalten
   * macht das CSS ab 1024 px.
   */
  zweispaltig = false;
  /** Was die beste Karte nach Stimme oder Kopieren meldet; "Zu dieser Antwort" zieht es nach. */
  besteKennzahlen: KartenKennzahlen | null = null;
  /** "Weitere, weniger passende Treffer" aufgeklappt; jede neue Suche beginnt zu. */
  weitereOffen = false;
  /** Gruppe und Typ, die alle Karten zeigen ("Alle N … zeigen"). */
  private aufgeklappt = new Set<string>();

  /** Aehnliche Aussagen aus "Nicht dabei?", ohne die der Treffer; fuer "Nicht gemeint?". */
  alternativen: StatementSearchResult[] = [];
  /** "Nicht gemeint?" klappt die Alternativen erst auf. */
  alternativenOffen = false;

  constructor(
    private searchService: SearchService,
    private stateService: StateManagementService,
    private router: Router,
    private route: ActivatedRoute,
    private breakpointObserver: BreakpointObserver,
    private cdr: ChangeDetectorRef,
    private teilenService: TeilenService,
  ) {
    this.searchQuery$ = this.stateService.searchQuery$;
    this.searchResponse$ = this.stateService.searchResults$;
    this.loading$ = this.stateService.loading$;
    this.error$ = this.stateService.error$;
  }

  ngOnInit(): void {
    this.breakpointObserver.observe(['(max-width: 599px)'])
      .pipe(takeUntil(this.destroy$))
      .subscribe(result => {
        this.isMobile = result.matches;
        this.cdr.markForCheck();
      });

    this.searchResponse$
      .pipe(takeUntil(this.destroy$))
      .subscribe(response => {
        this.antwort = response;
        this.karten = new WeakMap();
        // Eine neue Suche beginnt ohne Themenfilter und zugeklappt.
        this.aktivesThema = null;
        this.aufgeklappt.clear();
        this.alternativenOffen = false;
        this.weitereOffen = false;
        // Die Alternativen gehoeren zur vorigen Suche; "Nicht dabei?" meldet neu.
        this.alternativen = [];
        this.erkannt = response ? erkannteAussage(response) : null;
        this.themenDerTreffer = response ? themenDerTreffer(response, erkannterSchluessel(this.erkannt)) : [];
        this.anzeigen();
      });

    // Ohne Suchtext kommt man nicht hierher: ohneSuchtextZumStart (#642, R50).
    this.queryParamsSubscription = this.route.queryParams.subscribe(params => {
      this.searchQuery = params['searchQuery'] || '';
      if (this.searchQuery) {
        this.performSearch();
      }
    });
  }

  /** Nach einem Thema filtern; null = alle. */
  nachThemaFiltern(thema: string | null): void {
    this.aktivesThema = thema;
    this.anzeigen();
  }

  /** Gruppen und Zaehler aus der Suchantwort, gefiltert nach dem aktiven Thema. */
  private anzeigen(): void {
    const response = this.antwort ? nachThemaGefiltert(this.antwort, this.aktivesThema) : null;
    this.angezeigt = response;
    this.anzahlAlle = anzahlJeTyp(response);
    this.gruppen = response ? gruppieren(response, erkannterSchluessel(this.erkannt), this.karteZu) : [];
    this.anzahl = anzahlSichtbar(this.gruppen);
    this.bekannteAktualisieren();
    this.ansichtAktualisieren();
  }

  /**
   * Alle Typen, ohne Typwahl: Die Abschnittstitel tragen die Typen (V3, Designrunde
   * 17.11.). Die beste Antwort steht ganz da, alle anderen Karten eingeklappt.
   */
  private ansichtAktualisieren(): void {
    this.ansicht = besteHervorheben(ansichtBauen(this.gruppen, this.aufgeklappt));
    this.hauptGruppen = this.ansicht.filter((g) => !g.weniger);
    this.weitereGruppen = this.ansicht.filter((g) => g.weniger);
    this.weitereAnzahl = this.weitereGruppen.reduce((summe, g) => summe + g.anzahl, 0);
    this.zweispaltig = mitZweiterSpalte(this.hauptGruppen[0]);
    this.cdr.markForCheck();
  }

  /** Gruppen und Typen behalten ihre Karten, wenn sich Filter oder Aufklappen aendern. */
  nachGruppe(_index: number, gruppe: AnsichtGruppe): string {
    return gruppe.schluessel;
  }

  nachTyp(_index: number, block: { typ: TrefferTyp }): string {
    return block.typ;
  }

  /**
   * Aussagen, die "Nicht dabei?" nicht noch einmal vorschlaegt: die Aussage der Suche und
   * die der offenen Gruppen. Eingeklappte Aussagen bleiben als Alternative unter
   * "Nicht gemeint?" waehlbar.
   */
  private bekannteAktualisieren(): void {
    const ids = this.gruppen
      .filter((g) => !istWeniger(g, this.gruppen) && g.art !== 'ohne' && !g.schluessel.startsWith('text:'))
      .map((g) => g.schluessel);
    const neu = [...new Set([this.antwort?.statement_id, ...ids].filter((id): id is string => !!id))];
    if (neu.join('|') !== this.bekannteAussagen.join('|')) {
      this.bekannteAussagen = neu;
    }
  }

  /** Irgendein Treffer, gleich welchen Typs. */
  get hatTreffer(): boolean {
    return TREFFER_TYPEN.some((typ) => this.anzahlAlle[typ] > 0);
  }

  /**
   * "Alle N … zeigen": den Rest des Typs in dieser Gruppe zeigen und den Fokus auf
   * die erste neue Karte setzen, damit Tastatur und Screenreader dort weiterlesen.
   */
  alleZeigen(gruppe: AnsichtGruppe, typ: TrefferTyp, blockId: string, bisher: number): void {
    this.aufgeklappt.add(aufklappSchluessel(gruppe.schluessel, typ));
    this.ansichtAktualisieren();
    this.cdr.detectChanges();
    const block = document.getElementById(blockId);
    const neue = block?.querySelectorAll('app-beitragskarte')[bisher];
    const ziel =
      neue?.querySelector<HTMLElement>('a.titel-link, button, [tabindex="0"]') ??
      block?.querySelector<HTMLElement>('.typ-ueberschrift');
    ziel?.focus();
  }

  /** "Nicht dabei?" hat aehnliche Aussagen geladen; "Nicht gemeint?" bietet die ersten an. */
  alternativenGeladen(aussagen: StatementSearchResult[]): void {
    // Nach der laufenden Pruefung: Die Zeile "Erkannt als" steht im Template vor "Nicht dabei?".
    Promise.resolve().then(() => {
      this.alternativen = aussagen.slice(0, ALTERNATIVEN_ERKANNT);
      this.cdr.markForCheck();
    });
  }

  /**
   * Was geteilt wird, in Link und Text: die erkannte Aussage, nicht der rohe Suchtext.
   * Der kann ein eingefuegter fremder Post samt Namen sein; ohne erkannte Aussage geht
   * er deshalb nur gekuerzt mit (B7, Review zu #675).
   */
  private get geteilteAussage(): string {
    const erkannt = this.erkannt?.text?.trim();
    return erkannt || suchtextKuerzen(this.searchQuery);
  }

  get ergebnisTeilenBeschriftung(): string {
    return `Ergebnis teilen: Antworten auf „${this.geteilteAussage}“`;
  }

  /**
   * "Ergebnis teilen" (B7, docs/VISION.md): der Link auf die Suche nach der
   * erkannten Aussage, ueber das Teilen-Menue, wo das Geraet eines hat, sonst in die Zwischenablage. Zaehlt nicht als Nutzung, es ist keine
   * Karte (VISION: "eine Ergebnisseite teilen ... zaehlt nicht").
   */
  async ergebnisTeilen(): Promise<void> {
    if (!this.searchQuery.trim()) {
      return;
    }
    await this.teilenService.teilen({
      url: sucheLink(this.geteilteAussage),
      text: `Antworten auf: „${this.geteilteAussage}“`,
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
    this.queryParamsSubscription?.unsubscribe();
  }

  /**
   * Neue Suche. Die Aussage zur Suchanfrage legt das Backend im Suchaufruf selbst
   * an und liefert ihre ID in der Antwort (statement_id) - die Ansicht ruft dafuer
   * nichts Eigenes mehr auf. Frueher tat sie das ueber /statement/*, und fuer
   * Anonyme endete das mit 401 und einem Sprung auf /login.
   */
  private performSearch(): void {
    // Ergebnisse und Aussage der vorigen Suche gelten nicht mehr - und zwar ab
    // sofort, nicht erst mit loading=true. Wer in diesem Fenster auf "hinzufuegen"
    // tippt, darf nicht an die alte Aussage antworten.
    this.stateService.neueSucheBeginnen();
    this.fetchSearchResults();
  }

  private fetchSearchResults(): void {
    this.searchService.search(this.searchQuery, 10).subscribe();
  }

  retrySearch = (): void => {
    this.fetchSearchResults();
  }

  /**
   * Ins Formular des Typs, als Antwort auf die erkannte Aussage, wo es eine mit ID gibt,
   * sonst auf die Aussage der Suche per ID, sonst mit dem Suchtext. Die erkannte zuerst:
   * Legt die Suche eine eigene Aussage an (dieselbe Behauptung in anderen Worten),
   * liefert getById sie Nicht-Admins nicht aus (#436), und die Antwort landete an einer
   * Fast-Dublette statt an der Aussage, die das Kopfband nennt (#680).
   */
  /**
   * Nur einen Link dazu (UX-Review B13): in den Fangkorb einwerfen statt gleich
   * antworten. Besucher fuehrt der Guard zur Anmeldung und danach dorthin.
   */
  zumEinwerfen(): void {
    this.router.navigate([ROUTES.RAW_INPUT]);
  }

  navigateToContribute(typ: 'commentary' | 'generictext'): void {
    const { searchResults, loading } = this.stateService.currentState;
    // Waehrend eine Suche laeuft, stehen noch die Ergebnisse der vorigen im Zustand.
    const erkannt = this.erkannt?.id;
    const ausAntwort = loading
      ? null
      : istAussageId(erkannt)
        ? erkannt
        : istAussageId(searchResults?.statement_id)
          ? searchResults!.statement_id
          : null;
    this.router.navigate([FORMULAR_PFAD[typ]], {
      queryParams: aussageParameterMitText(ausAntwort, this.searchQuery),
    });
  }
}
