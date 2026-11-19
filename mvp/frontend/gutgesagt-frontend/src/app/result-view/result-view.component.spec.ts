import { ChangeDetectorRef } from '@angular/core';
import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { BreakpointObserver } from '@angular/cdk/layout';
import { BehaviorSubject, of } from 'rxjs';
import { map } from 'rxjs/operators';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter, Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';

import { ResultViewComponent, erkannteAussage, themenDerTreffer } from './result-view.component';
import { By } from '@angular/platform-browser';
import { BeitragskarteComponent } from '../beitragskarte/beitragskarte.component';
import { AuthService } from '../auth/auth.service';
import { StatementService } from '../services/statement.service';
import { routes } from '../app.routes';
import { ohneWaechter } from '../testing/routen-ohne-waechter';
import { StateManagementService } from '../services/state-management.service';
import { Clipboard } from '@angular/cdk/clipboard';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TEILEN_LINK_KOPIERT, TEILEN_NAVIGATOR, TeilenNavigator } from '../shared/teilen.service';

/** Die Karten, wie sie dastehen, ueber alle Gruppen und Typen. */
function kartenIds(komponente: ResultViewComponent): string[] {
  return komponente.ansicht.flatMap((g) => g.bloecke.flatMap((b) => b.karten.map((k) => k.id)));
}

describe('ResultViewComponent', () => {
  let component: ResultViewComponent;
  let fixture: ComponentFixture<ResultViewComponent>;

  beforeEach(async () => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([
           {
              path: 'result-view',
              component: ResultViewComponent
           }
        ]),
      ],
      imports: [
        ResultViewComponent
      ]
    });

    const harness = await RouterTestingHarness.create();
    component = await harness.navigateByUrl(
      'result-view?searchQuery=testQuery',
      ResultViewComponent
    );
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should have the searchQuery set', () => {
    expect(component.searchQuery).toEqual('testQuery');
  });
});

/**
 * Leere Suche, echter Klick auf "hinzufuegen", echte Routentabelle: Der Weg fuehrt
 * auf die Formularseite des Typs, mit der Aussage dieser Suche per ID.
 */
describe('ResultViewComponent: Klick auf Hinzufuegen bei leerer Suche', () => {
  const AUSSAGE_ID = '11111111-2222-4333-8444-555555555555';

  let fixture: ComponentFixture<ResultViewComponent>;
  let router: Router;

  function oeffnen(mobil: boolean, statementId: string | null): void {
    TestBed.configureTestingModule({
      imports: [ResultViewComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter(ohneWaechter(routes)),
        {
          provide: BreakpointObserver,
          useValue: { observe: (query: string[]) => of({ matches: mobil && query[0] === '(max-width: 599px)', breakpoints: {} }) },
        },
      ],
    });

    router = TestBed.inject(Router);
    TestBed.inject(StateManagementService).setSearchResults({
      query_was_newly_added_as_statement: false,
      statement_id: statementId,
      statement_text: 'waermepumpe teuer',
      commentary_search_results_count: 0,
      commentary_search_results: [],
      generictext_search_results_count: 0,
      generictext_search_results: [],
    });
    fixture = TestBed.createComponent(ResultViewComponent);
    fixture.detectChanges();
    // ngOnInit liest searchQuery aus der Adresse und wuerde dann suchen - hier
    // steht die Antwort schon im Zustand, deshalb wird der Text danach gesetzt.
    fixture.componentInstance.searchQuery = 'waermepumpe teuer';
  }

  function knopf(bereich: string, nr: number): HTMLButtonElement {
    const knoepfe: HTMLButtonElement[] = Array.from(fixture.nativeElement.querySelectorAll(`${bereich} button`));
    expect(knoepfe.length).withContext(`Knoepfe in ${bereich}`).toBe(2);
    return knoepfe[nr];
  }

  /**
   * Wohin der letzte Klick fuehren sollte, ohne wirklich zu navigieren: Die Seite ist
   * im Test nicht geroutet und saehe sonst ?searchQuery= der Formularadresse als neue
   * Suche.
   */
  function zielMerken(): () => string {
    const navigieren = spyOn(router, 'navigate').and.resolveTo(true);
    return () => {
      const [befehle, extras] = navigieren.calls.mostRecent().args;
      return router.serializeUrl(router.createUrlTree(befehle, extras));
    };
  }

  it('fuehrt am Desktop in beide Formulare, mit ID und Text', fakeAsync(() => {
    oeffnen(false, AUSSAGE_ID);
    const ziel = zielMerken();

    knopf('.action-buttons-top', 0).click();
    tick();
    expect(ziel()).toBe(`/workflow/add-commentary?aussage=${AUSSAGE_ID}&searchQuery=waermepumpe%20teuer`);

    knopf('.action-buttons-top', 1).click();
    tick();
    expect(ziel()).toBe(`/workflow/add-generictext?aussage=${AUSSAGE_ID}&searchQuery=waermepumpe%20teuer`);
  }));

  it('fuehrt am Handy ebenso dorthin', fakeAsync(() => {
    oeffnen(true, AUSSAGE_ID);

    knopf('.action-buttons-top', 0).click();
    tick();
    expect(router.url).toBe(`/workflow/add-commentary?aussage=${AUSSAGE_ID}&searchQuery=waermepumpe%20teuer`);
  }));

  for (const fehlend of [null, '', 'None']) {
    it(`nimmt bei fehlender ID (${JSON.stringify(fehlend)}) den Suchtext`, fakeAsync(() => {
      oeffnen(false, fehlend);

      knopf('.action-buttons-top', 0).click();
      tick();
      expect(router.url).toBe('/workflow/add-commentary?searchQuery=waermepumpe%20teuer');
    }));
  }

  it('laesst nach Suchbeginn keine alte Aussage-ID stehen', fakeAsync(() => {
    oeffnen(false, AUSSAGE_ID);
    const zustand = TestBed.inject(StateManagementService);
    const http = TestBed.inject(HttpTestingController);
    expect(knopf('.action-buttons-top', 0)).withContext('Knopf der vorigen Suche').toBeTruthy();

    // Neue Suche startet; die Antwort bleibt hier offen.
    const komponente = fixture.componentInstance as unknown as { performSearch(): void };
    komponente.performSearch();
    fixture.detectChanges();

    http.expectOne((req) => req.url.endsWith('/api/v1/search/searchByText'));
    expect(zustand.currentState.searchResults).toBeNull();
    expect(fixture.nativeElement.querySelectorAll('.action-buttons-top button').length)
      .withContext('kein Hinzufuegen-Knopf der alten Suche mehr')
      .toBe(0);

    // Auch ein Aufruf aus einem anderen Einstieg nimmt jetzt den Text, nicht die alte ID.
    fixture.componentInstance.navigateToContribute('commentary');
    tick();
    expect(router.url).toBe('/workflow/add-commentary?searchQuery=waermepumpe%20teuer');
  }));

  it('ruft beim Suchen keinen Statement-Endpunkt auf (anonym waere das 401 und /login)', fakeAsync(() => {
    oeffnen(false, AUSSAGE_ID);
    const http = TestBed.inject(HttpTestingController);

    (fixture.componentInstance as unknown as { performSearch(): void }).performSearch();
    tick();

    http.expectOne((req) => req.url.endsWith('/api/v1/search/searchByText'));
    http.expectNone((req) => req.url.includes('/api/v1/statement/'));
    expect(router.url).not.toContain('/login');
  }));
});

/**
 * Themenfilter (#363): Die Treffer tragen die Themen der Aussage, ueber die sie
 * gefunden wurden. Der Filter bietet nur diese Themen an und zeigt danach nur die
 * Treffer mit dem gewaehlten Thema.
 */
describe('ResultViewComponent: Filter nach Thema', () => {
  const KLIMA = { schluessel: 'klima', name: 'Klima' };
  const VERKEHR = { schluessel: 'verkehr', name: 'Verkehr' };

  let fixture: ComponentFixture<ResultViewComponent>;

  function kommentar(id: string, titel: string, themen: Array<{ schluessel: string; name: string }>) {
    return {
      score: 0.9,
      statement_text: 'Tempolimit bringt nichts',
      statement_similarity_score: 0.9,
      reply_relevance: 0.9,
      statement_id: `aussage-${id}`,
      themen,
      commentary_result: { id, content_type: 'commentary', title: titel, text: 'Text', references: [] },
    } as any;
  }

  function oeffnen(mobil: boolean, kommentare: any[]): HTMLElement {
    TestBed.configureTestingModule({
      imports: [ResultViewComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter(ohneWaechter(routes)),
        {
          provide: BreakpointObserver,
          useValue: { observe: (query: string[]) => of({ matches: mobil && query[0] === '(max-width: 599px)', breakpoints: {} }) },
        },
      ],
    });
    TestBed.inject(StateManagementService).setSearchResults({
      query_was_newly_added_as_statement: false,
      statement_id: null,
      statement_text: 'tempolimit',
      commentary_search_results_count: kommentare.length,
      commentary_search_results: kommentare,
      generictext_search_results_count: 0,
      generictext_search_results: [],
      post_search_results_count: 0,
      post_search_results: [],
    });
    fixture = TestBed.createComponent(ResultViewComponent);
    fixture.detectChanges();
    return fixture.nativeElement;
  }

  function filterKnoepfe(seite: HTMLElement): HTMLButtonElement[] {
    return Array.from(seite.querySelectorAll('app-themen-filter button'));
  }

  for (const mobil of [false, true]) {
    const wo = mobil ? 'Handy' : 'Desktop';

    it(`bietet nur die Themen der Treffer an (${wo})`, () => {
      const seite = oeffnen(mobil, [
        kommentar('k-1', 'Tempo 120 spart CO2', [VERKEHR, KLIMA]),
        kommentar('k-2', 'Tempolimit rettet Leben', [VERKEHR]),
      ]);

      expect(filterKnoepfe(seite).map((k) => k.textContent?.trim())).toEqual(['Alle Themen', 'Verkehr', 'Klima']);
    });

    it(`zeigt nach der Wahl nur die Treffer mit diesem Thema (${wo})`, () => {
      const seite = oeffnen(mobil, [
        kommentar('k-1', 'Tempo 120 spart CO2', [VERKEHR, KLIMA]),
        kommentar('k-2', 'Tempolimit rettet Leben', [VERKEHR]),
      ]);

      filterKnoepfe(seite).find((k) => k.textContent?.trim() === 'Klima')!.click();
      fixture.detectChanges();

      expect(kartenIds(fixture.componentInstance)).toEqual(['k-1']);
      expect(seite.textContent).toContain('Tempo 120 spart CO2');
      expect(seite.textContent).not.toContain('Tempolimit rettet Leben');

      filterKnoepfe(seite).find((k) => k.textContent?.trim() === 'Alle Themen')!.click();
      fixture.detectChanges();
      expect(kartenIds(fixture.componentInstance)).toEqual(['k-1', 'k-2']);
    });

    it(`zeigt keinen Filter, wenn kein Treffer ein Thema hat (${wo})`, () => {
      const seite = oeffnen(mobil, [kommentar('k-1', 'Tempo 120 spart CO2', [])]);

      expect(seite.querySelector('app-themen-filter')).toBeNull();
    });
  }

  it('setzt den Filter mit einer neuen Suche zurueck', () => {
    oeffnen(false, [kommentar('k-1', 'Tempo 120 spart CO2', [KLIMA])]);
    fixture.componentInstance.nachThemaFiltern('klima');

    TestBed.inject(StateManagementService).setSearchResults({
      query_was_newly_added_as_statement: false,
      statement_id: null,
      statement_text: 'andere suche',
      commentary_search_results_count: 1,
      commentary_search_results: [kommentar('k-9', 'Etwas anderes', [VERKEHR])],
      generictext_search_results_count: 0,
      generictext_search_results: [],
      post_search_results_count: 0,
      post_search_results: [],
    });

    expect(fixture.componentInstance.aktivesThema).toBeNull();
    expect(kartenIds(fixture.componentInstance)).toEqual(['k-9']);
  });
});

/**
 * "Nicht dabei?" (#362): Ohne Treffer und unter den Treffern stehen aehnliche
 * Aussagen und der Weg zum Neu-Anlegen; die Suche endet nie in einer Sackgasse.
 */
describe('ResultViewComponent: Nicht dabei?', () => {
  const AUSSAGE_ID = '11111111-2222-4333-8444-555555555555';
  const TREFFER_AUSSAGE = '22222222-2222-4333-8444-555555555555';
  const AEHNLICH = { id: '33333333-2222-4333-8444-555555555555', text: 'Wärmepumpen lohnen sich nicht', replysuggestions_count: 2, score: 0.9 };
  const SCHON_DA = { id: TREFFER_AUSSAGE, text: 'Wärmepumpen sind zu teuer', replysuggestions_count: 2, score: 0.95 };

  let fixture: ComponentFixture<ResultViewComponent>;
  let router: Router;
  let statementService: jasmine.SpyObj<StatementService>;

  const KOMMENTAR = {
    score: 0.9,
    statement_id: TREFFER_AUSSAGE,
    statement_text: 'Wärmepumpen sind zu teuer',
    statement_similarity_score: 0.9,
    reply_relevance: 0.8,
    commentary_result: {
      id: 'k-1',
      content_type: 'commentary',
      title: 'Ein Kommentar',
      text: 'Gefoerdert wird bis zu 70 Prozent.',
      references: [],
    },
  };

  function oeffnen(mobil: boolean, mitTreffer: boolean, vorschlaege = [SCHON_DA, AEHNLICH]): HTMLElement {
    statementService = jasmine.createSpyObj('StatementService', ['aehnlicheAussagen']);
    statementService.aehnlicheAussagen.and.returnValue(of(vorschlaege));
    TestBed.configureTestingModule({
      imports: [ResultViewComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter(ohneWaechter(routes)),
        { provide: StatementService, useValue: statementService },
        {
          provide: BreakpointObserver,
          useValue: { observe: (query: string[]) => of({ matches: mobil && query[0] === '(max-width: 599px)', breakpoints: {} }) },
        },
      ],
    });
    router = TestBed.inject(Router);
    TestBed.inject(AuthService).setUserInfo({ isAuthenticated: true, userId: 'u-1', userName: 'Test', claims: null });
    TestBed.inject(StateManagementService).setSearchResults({
      query_was_newly_added_as_statement: true,
      statement_id: AUSSAGE_ID,
      statement_text: 'waermepumpe teuer',
      commentary_search_results_count: mitTreffer ? 1 : 0,
      commentary_search_results: mitTreffer ? [KOMMENTAR as any] : [],
      generictext_search_results_count: 0,
      generictext_search_results: [],
    });
    fixture = TestBed.createComponent(ResultViewComponent);
    fixture.detectChanges();
    // ngOnInit liest searchQuery aus der (hier leeren) Adresse; der Text kommt danach.
    fixture.componentInstance.searchQuery = 'waermepumpe teuer';
    fixture.debugElement.injector.get(ChangeDetectorRef).markForCheck();
    fixture.detectChanges();
    return fixture.nativeElement;
  }

  function aehnliche(seite: HTMLElement): string[] {
    return Array.from(seite.querySelectorAll('.aehnliche-aussage .aussage-text')).map((e) => (e.textContent ?? '').trim());
  }

  it('sagt ohne Treffer, dass noch nichts drin ist, und zeigt aehnliche Aussagen', () => {
    const seite = oeffnen(false, false);

    expect(seite.querySelector('.unified-empty-state .search-query-info')?.textContent)
      .toContain('Zu „waermepumpe teuer“ ist noch nichts drin.');
    expect(seite.querySelector('.unified-empty-state app-nicht-dabei')?.textContent).toContain('Meintest du …?');
    expect(statementService.aehnlicheAussagen).toHaveBeenCalledWith('waermepumpe teuer');
    expect(aehnliche(seite)).toEqual(['Wärmepumpen sind zu teuer', 'Wärmepumpen lohnen sich nicht']);
  });

  // UX-Review B13: dritter Weg "nur einen Link" und der Hinweis, dass nicht jede Aussage eine Antwort braucht
  it('bietet ohne Treffer "Nur einen Link dazu? Einwerfen" und den Hinweis zur Antwort', () => {
    const seite = oeffnen(true, false);
    const bereich = seite.querySelector<HTMLElement>('.unified-empty-state')!;
    const navigate = spyOn(router, 'navigate').and.resolveTo(true);

    expect(bereich.querySelector('.nur-link')?.textContent).toContain('Nur einen Link dazu?');
    expect(bereich.querySelector('.keine-antwort-noetig')?.textContent).toContain('Nicht jede Aussage braucht eine Antwort.');
    bereich.querySelector<HTMLButtonElement>('.nur-link button')!.click();
    expect(navigate).toHaveBeenCalledWith(['/einwerfen']);
  });

  it('gibt ohne Treffer einen Suchtipp, der zur Suche nach Aussagen passt (#617)', () => {
    const seite = oeffnen(false, false);
    const tipp = seite.querySelector('.unified-empty-state .such-tipp')?.textContent ?? '';
    expect(tipp).toContain('Gib die Aussage so ein, wie du sie gehört hast.');
    expect(seite.textContent).not.toContain('Formuliere eine konkrete Frage');
  });

  it('bietet ohne Treffer die Aussage der Suche nicht als aehnliche an (sonst Schleife)', () => {
    const seite = oeffnen(false, false, [{ ...AEHNLICH, id: AUSSAGE_ID, text: 'waermepumpe teuer' }, AEHNLICH]);
    expect(aehnliche(seite)).toEqual(['Wärmepumpen lohnen sich nicht']);
  });

  it('fuehrt ohne Treffer mit "Antworten" ins Kommentarformular, Aussage vorbelegt', fakeAsync(() => {
    const seite = oeffnen(true, false);
    const knopf = seite.querySelector<HTMLButtonElement>('.unified-empty-state app-nicht-dabei .action-buttons-top button')!;
    expect(knopf.textContent).toContain('Antworten');

    knopf.click();
    tick();
    expect(router.url).toBe(`/workflow/add-commentary?aussage=${AUSSAGE_ID}&searchQuery=waermepumpe%20teuer`);
  }));

  it('zeigt am Desktop unter den Treffern "Nicht dabei?" ohne die Aussage der Treffer', fakeAsync(() => {
    const seite = oeffnen(false, true);
    const unten = seite.querySelector<HTMLElement>('.nicht-dabei-unten')!;

    expect(seite.querySelector('.unified-empty-state')).toBeNull();
    expect(unten.textContent).toContain('Nicht dabei?');
    expect(aehnliche(unten)).toEqual(['Wärmepumpen lohnen sich nicht']);

    // "Schreib selbst einen Kommentar zu dieser Aussage": die der Treffer, nicht die
    // der Suche (getById liefert eine eigene Suchanfrage Nicht-Admins nicht aus, #436).
    unten.querySelector<HTMLButtonElement>('.neu-anlegen-knopf button')!.click();
    tick();
    expect(router.url).toBe(`/workflow/add-commentary?aussage=${TREFFER_AUSSAGE}&searchQuery=waermepumpe%20teuer`);
  }));

  it('sucht mit einem Klick auf eine aehnliche Aussage nach ihr', fakeAsync(() => {
    const seite = oeffnen(false, true);

    seite.querySelector<HTMLAnchorElement>('.nicht-dabei-unten .aehnliche-aussage')!.click();
    tick();
    expect(router.url).toBe('/result?searchQuery=W%C3%A4rmepumpen%20lohnen%20sich%20nicht');
  }));
});

/** 0 Treffer: Wortlaut und "Oft gesucht" als Anschluss (#642, R49, R51). */
describe('ResultViewComponent: ohne Treffer', () => {
  function oeffnen(mobil: boolean): HTMLElement {
    TestBed.configureTestingModule({
      imports: [ResultViewComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter(ohneWaechter(routes)),
        {
          provide: BreakpointObserver,
          useValue: { observe: (query: string[]) => of({ matches: mobil && query[0] === '(max-width: 599px)', breakpoints: {} }) },
        },
      ],
    });
    TestBed.inject(StateManagementService).setSearchResults({
      query_was_newly_added_as_statement: true,
      statement_id: null,
      statement_text: 'xyz',
      commentary_search_results_count: 0,
      commentary_search_results: [],
      generictext_search_results_count: 0,
      generictext_search_results: [],
    });
    const fixture = TestBed.createComponent(ResultViewComponent);
    fixture.detectChanges();
    return fixture.nativeElement;
  }

  for (const mobil of [false, true]) {
    const bereich = '.unified-empty-state';
    it(`bietet "Oft gesucht" und sagt "zu dieser Aussage" (${mobil ? 'Handy' : 'Desktop'})`, () => {
      const seite = oeffnen(mobil);
      const leer = seite.querySelector(bereich)!;
      expect(leer.querySelector('app-oft-gesucht')).withContext('Anschluss statt Sackgasse').toBeTruthy();
      expect(leer.querySelector('.hier-fehlt-link')?.getAttribute('href')).toBe('/hier-fehlt-eine-antwort');
      expect(leer.querySelector('.neu-anlegen-satz')?.textContent?.trim()).toBe('Schreib den ersten Kommentar zu dieser Aussage.');
      expect(seite.querySelector('.kopfband')).toBeNull();
      expect(seite.querySelector('.typ-chips')).toBeNull();
    });
  }
});

describe('erkannteAussage', () => {
  const treffer = (statement_id: string | null, statement_text: string, score: number) =>
    ({ score, statement_text, statement_id }) as any;
  const antwort = (kommentare: any[], hintergrund: any[] = []) => ({
    query_was_newly_added_as_statement: false,
    statement_id: null,
    statement_text: '',
    commentary_search_results_count: kommentare.length,
    commentary_search_results: kommentare,
    generictext_search_results_count: hintergrund.length,
    generictext_search_results: hintergrund,
  });

  it('nimmt die Aussage der meisten Treffer, ueber alle Typen', () => {
    expect(erkannteAussage(antwort([treffer('a', 'A', 0.9)], [treffer('b', 'B', 0.8), treffer('b', 'B', 0.7)])))
      .toEqual({ id: 'b', text: 'B' });
  });

  it('nimmt bei Gleichstand die Aussage mit dem besten Treffer', () => {
    expect(erkannteAussage(antwort([treffer('a', 'A', 0.7), treffer('b', 'B', 0.9)]))).toEqual({ id: 'b', text: 'B' });
  });

  it('erkennt Aussagen ohne ID an ihrem Text', () => {
    expect(erkannteAussage(antwort([treffer(null, ' A ', 0.9), treffer(null, 'A', 0.5)]))).toEqual({ id: null, text: 'A' });
  });

  it('gibt null, wenn die Aussage weder den obersten Treffer noch die Mehrheit traegt', () => {
    // b hat zwei Treffer, aber a den obersten; von vier Treffern ist b keine Mehrheit.
    expect(
      erkannteAussage(antwort([treffer('a', 'A', 0.95), treffer('b', 'B', 0.8), treffer('b', 'B', 0.7), treffer('c', 'C', 0.6)])),
    ).toBeNull();
  });

  it('nimmt eine Aussage mit Mehrheit auch ohne den obersten Treffer', () => {
    expect(erkannteAussage(antwort([treffer('a', 'A', 0.95), treffer('b', 'B', 0.8), treffer('b', 'B', 0.7)])))
      .toEqual({ id: 'b', text: 'B' });
  });

  it('zaehlt Bilder mit', () => {
    const mitBildern = {
      ...antwort([treffer('a', 'A', 0.9)]),
      image_search_results_count: 2,
      image_search_results: [treffer('b', 'B', 0.8), treffer('b', 'B', 0.7)],
    };
    expect(erkannteAussage(mitBildern)).toEqual({ id: 'b', text: 'B' });
  });

  it('gibt null, wenn nur direkte Treffer ohne Aussage da sind', () => {
    expect(erkannteAussage(antwort([treffer(null, '', 0.9)]))).toBeNull();
  });
});

/**
 * Eine Darstellung fuer Handy und Desktop (K2+): Kopfband mit der erkannten Aussage,
 * Chips je Typ, Treffer nach Aussage gruppiert, je Typ zuerst hoechstens drei Karten.
 */
describe('ResultViewComponent: Zeile "Erkannt als", beste Antwort und Gruppen je Aussage', () => {
  const ERKANNT_ID = '22222222-2222-4333-8444-555555555555';
  const ANDERE_ID = '44444444-2222-4333-8444-555555555555';
  const ERKANNT = 'Windräder töten die Vögel!';
  const ANDERE = 'Windkraft zerstört die Landschaft!';
  const AEHNLICH = [
    { id: '55555555-2222-4333-8444-555555555555', text: 'Windräder sind zu laut', replysuggestions_count: 1, score: 0.8 },
    { id: '66666666-2222-4333-8444-555555555555', text: 'Infraschall macht krank', replysuggestions_count: 0, score: 0.7 },
  ];

  type Typ = 'commentary' | 'generictext' | 'image' | 'post';
  const FELD: Record<Typ, string> = {
    commentary: 'commentary_result',
    generictext: 'generictext_result',
    image: 'image_result',
    post: 'post_result',
  };
  const INHALTSTYP: Record<Typ, string> = { commentary: 'commentary', generictext: 'generic_text', image: 'image', post: 'post' };

  function treffer(typ: Typ, id: string, statementId: string | null, statementText: string, score: number): any {
    const inhalt: any = { id, content_type: INHALTSTYP[typ], title: `Titel ${id}`, text: 'Text', references: [] };
    if (typ === 'image') {
      inhalt.image_url = '/marke/icon-192.png';
    }
    if (typ === 'post') {
      Object.assign(inhalt, { platform: 'bluesky', url: 'https://example.org/p/1', engagement: 0 });
    }
    return {
      score,
      statement_id: statementId,
      statement_text: statementText,
      statement_similarity_score: 0.9,
      reply_relevance: 0.8,
      [FELD[typ]]: inhalt,
    };
  }
  const erkannt = (typ: Typ, id: string, score: number) => treffer(typ, id, ERKANNT_ID, ERKANNT, score);
  const andere = (typ: Typ, id: string, score: number) => treffer(typ, id, ANDERE_ID, ANDERE, score);
  const direkt = (typ: Typ, id: string, score: number) => treffer(typ, id, null, '', score);

  function antwort(t: { k?: any[]; h?: any[]; b?: any[]; p?: any[] }): any {
    const k = t.k ?? [], h = t.h ?? [], b = t.b ?? [], p = t.p ?? [];
    return {
      query_was_newly_added_as_statement: false,
      statement_id: '11111111-2222-4333-8444-555555555555',
      statement_text: 'windraeder voegel',
      commentary_search_results_count: k.length,
      commentary_search_results: k,
      generictext_search_results_count: h.length,
      generictext_search_results: h,
      image_search_results_count: b.length,
      image_search_results: b,
      post_search_results_count: p.length,
      post_search_results: p,
    };
  }

  /** Erkannte Aussage mit allen vier Typen, eine aehnliche und ein direkter Treffer. */
  const GEMISCHT = () =>
    antwort({
      k: [erkannt('commentary', 'k-1', 0.9), andere('commentary', 'k-2', 0.85), erkannt('commentary', 'k-3', 0.8), direkt('commentary', 'k-4', 0.5)],
      h: [erkannt('generictext', 'h-1', 0.7)],
      b: [erkannt('image', 'b-1', 0.75), andere('image', 'b-2', 0.6)],
      p: [erkannt('post', 'p-1', 0.65)],
    });

  let fixture: ComponentFixture<ResultViewComponent>;
  let router: Router;
  /** Das Teilen-Menue des Geraets; ohne share wie am Desktop ohne Web Share API. */
  let nav: TeilenNavigator;

  beforeEach(() => (nav = {}));

  /** Ab 1024 px (Desktop-Signal der Seite); per next() laesst sich die Breite wechseln. */
  let breit: BehaviorSubject<boolean>;

  async function oeffnen(mobil: boolean, suchantwort: any, aehnliche: any[] = AEHNLICH, abDesktop = false): Promise<HTMLElement> {
    breit = new BehaviorSubject(abDesktop);
    const statementService = jasmine.createSpyObj('StatementService', ['aehnlicheAussagen']);
    statementService.aehnlicheAussagen.and.returnValue(of(aehnliche));
    TestBed.configureTestingModule({
      imports: [ResultViewComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter(ohneWaechter(routes)),
        { provide: StatementService, useValue: statementService },
        { provide: TEILEN_NAVIGATOR, useFactory: () => nav },
        {
          provide: BreakpointObserver,
          useValue: {
            observe: (query: string[]) =>
              query[0] === '(min-width: 1024px)'
                ? breit.pipe(map((matches) => ({ matches, breakpoints: {} })))
                : of({ matches: mobil && query[0] === '(max-width: 599px)', breakpoints: {} }),
          },
        },
      ],
    });
    router = TestBed.inject(Router);
    TestBed.inject(AuthService).setUserInfo({ isAuthenticated: true, userId: 'u-1', userName: 'Test', claims: null });
    TestBed.inject(StateManagementService).setSearchResults(suchantwort);
    fixture = TestBed.createComponent(ResultViewComponent);
    fixture.detectChanges();
    fixture.componentInstance.searchQuery = 'windraeder voegel';
    fixture.debugElement.injector.get(ChangeDetectorRef).markForCheck();
    fixture.detectChanges();
    // Die aehnlichen Aussagen fuer "Nicht gemeint?" kommen nach der Pruefung an (Promise).
    await fixture.whenStable();
    fixture.detectChanges();
    return fixture.nativeElement;
  }

  const text = (e: Element | null | undefined) => (e?.textContent ?? '').replace(/\s+/g, ' ').trim();
  const texte = (seite: Element, selektor: string) => Array.from(seite.querySelectorAll(selektor)).map(text);

  function neuZeichnen(): void {
    fixture.debugElement.injector.get(ChangeDetectorRef).markForCheck();
    fixture.detectChanges();
  }

  /** Die Aufklapp-Knoepfe der eingeklappten Karten. */
  const aufklapper = (seite: Element) => Array.from(seite.querySelectorAll<HTMLButtonElement>('.aufklapp-knopf'));

  for (const mobil of [false, true]) {
    const wo = mobil ? 'Handy' : 'Desktop';

    it(`gruppiert nach Aussage: erkannte zuerst, andere und direkte Treffer eingeklappt darunter (${wo})`, async () => {
      const seite = await oeffnen(mobil, GEMISCHT());
      // So, wie ein Screenreader die Ueberschrift liest: ohne das Symbol, mit Leerzeichen.
      const ueberschriften = () => Array.from(seite.querySelectorAll('.gruppe > h2')).map((h) => {
        const kopie = h.cloneNode(true) as HTMLElement;
        kopie.querySelectorAll('[aria-hidden="true"]').forEach((e) => e.remove());
        return (kopie.textContent ?? '').replace(/\s+/g, ' ').trim();
      });
      expect(ueberschriften()).toEqual([`Zu dieser Aussage: „${ERKANNT}“ 5 Treffer`]);
      const weitere = seite.querySelector<HTMLButtonElement>('.weitere-umschalter')!;
      expect(text(weitere)).toBe('expand_more Weitere, weniger passende Treffer (3)');
      expect(weitere.getAttribute('aria-expanded')).toBe('false');

      weitere.click();
      fixture.detectChanges();
      expect(weitere.getAttribute('aria-expanded')).toBe('true');
      expect(ueberschriften()).toEqual([
        `Zu dieser Aussage: „${ERKANNT}“ 5 Treffer`,
        `Zu einer anderen Aussage: „${ANDERE}“ 2 Treffer`,
        'Passt zu deinem Suchtext 1 Treffer',
      ]);
      expect(seite.querySelector('.mobile-tab-bar, app-result-carousel')).withContext('keine Tabs, kein Karussell').toBeNull();
    });

    it(`klappt im aufgeklappten Bereich "Weitere" die Karten nicht noch einmal ein (${wo})`, async () => {
      const seite = await oeffnen(mobil, GEMISCHT());
      seite.querySelector<HTMLButtonElement>('.weitere-umschalter')!.click();
      fixture.detectChanges();
      const karten = seite.querySelectorAll('.weitere-liste app-beitragskarte');
      expect(karten.length).toBe(3);
      karten.forEach((karte) => {
        expect(karte.querySelector('.aufklapp-knopf')).withContext('kein zweites Aufklappen').toBeNull();
        expect(karte.querySelector('.karte-inhalt')).withContext('Inhalt steht da').toBeTruthy();
      });
      // Die erkannte Gruppe bleibt wie gehabt: ausser der besten eingeklappt
      expect(seite.querySelector('.gruppe:not(.weitere-liste .gruppe) .eingeklappte-karten .aufklapp-knopf')).toBeTruthy();
    });

    it(`zeigt an den Karten keine eigene Antwort-auf-Zeile, die Gruppe traegt die Aussage (${wo})`, async () => {
      const seite = await oeffnen(mobil, GEMISCHT());
      seite.querySelector<HTMLButtonElement>('.weitere-umschalter')!.click();
      fixture.detectChanges();
      expect(seite.querySelectorAll('app-beitragskarte').length).toBe(8);
      expect(seite.querySelector('.statement-zeile, .statement-vorschau')).toBeNull();
    });

    it(`ordnet die Typen je Gruppe fest: die beste Antwort zuerst, die Titel tragen Typ und Zahl (${wo})`, async () => {
      const seite = await oeffnen(mobil, GEMISCHT());
      const ersteGruppe = seite.querySelector('.gruppe')!;
      expect(Array.from(ersteGruppe.querySelectorAll('.typ-block')).map((b) => b.getAttribute('data-typ')))
        .toEqual(['commentary', 'generictext', 'image', 'post']);
      expect(texte(ersteGruppe, '.typ-ueberschrift'))
        .toEqual(['Beste Antwort', 'Weitere Antworten · 1', 'Hintergrundinfo · 1', 'Bild · 1', 'Post · 1']);
      expect(seite.querySelector('.typ-erklaerung')).withContext('die Titel tragen die Typen (V3)').toBeNull();
    });

    it(`zeigt an den Abschnittstiteln kein ⓘ mehr, nur am Etikett der Karte (${wo})`, async () => {
      const seite = await oeffnen(mobil, GEMISCHT());
      const ersteGruppe = seite.querySelector('.gruppe')!;
      expect(ersteGruppe.querySelectorAll('.typ-kopf').length).toBe(4);
      expect(ersteGruppe.querySelector('.typ-kopf button, .typ-kopf mat-icon, .typ-info')).toBeNull();
      expect(seite.querySelector('.beste-ueberschrift')!.closest('.typ-kopf')).toBeNull();
    });

    it(`setzt "Zu dieser Antwort" zwischen die beste Antwort und die weiteren Karten (${wo})`, async () => {
      const seite = await oeffnen(mobil, GEMISCHT());
      const kaesten = seite.querySelectorAll('app-zu-dieser-antwort');
      expect(kaesten.length).withContext('genau einer, zur besten Antwort').toBe(1);
      const kasten = kaesten[0];
      expect(kasten.querySelector('h3')?.textContent?.trim()).toBe('Zu dieser Antwort');
      expect(kasten.querySelector('aside')?.getAttribute('aria-labelledby')).toBe(kasten.querySelector('h3')!.id);
      // Lese- und Tab-Reihenfolge: beste, Kasten, weitere
      const beste = seite.querySelector('.beste-antwort')!;
      const weitere = seite.querySelector('.eingeklappte-karten')!;
      expect(beste.compareDocumentPosition(kasten) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
      expect(kasten.compareDocumentPosition(weitere) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
      expect(kasten.textContent).toContain('4 Zeichen');
    });

    it(`stellt den Kasten auch neben die einzige Antwort (${wo})`, async () => {
      const seite = await oeffnen(mobil, antwort({ k: [erkannt('commentary', 'k-1', 0.9)] }));
      expect(seite.querySelector('.treffer-spalte')!.classList).toContain('zweispaltig');
      expect(seite.querySelectorAll('.gruppe.mit-bester app-zu-dieser-antwort').length).toBe(1);
    });

    it(`zeigt die beste Antwort ganz und alle anderen Karten eingeklappt (${wo})`, async () => {
      const seite = await oeffnen(mobil, GEMISCHT());
      const beste = seite.querySelectorAll('.beste-antwort app-beitragskarte');
      expect(beste.length).toBe(1);
      expect(text(beste[0].querySelector('.karte-titel'))).toBe('Titel k-1');
      expect(beste[0].querySelector('.aufklapp-knopf')).withContext('die beste ist nicht aufklappbar').toBeNull();
      expect(beste[0].querySelector('.karte-inhalt')).toBeTruthy();
      expect(beste[0].querySelector('.kopieren-knopf')).toBeTruthy();
      // Die beste steht vor allen anderen Karten, auch zweispaltig (DOM-Reihenfolge fuer Tastatur und Screenreader).
      expect(seite.querySelector('app-beitragskarte')).toBe(beste[0]);
      // Neben der besten gibt es weitere Karten: am Desktop zwei Spalten (CSS ab 1024 px)
      expect(seite.querySelector('.treffer-spalte')!.classList).toContain('zweispaltig');
      expect(seite.querySelectorAll('.gruppe.mit-bester').length).toBe(1);

      const eingeklappt = seite.querySelectorAll('.eingeklappte-karten app-beitragskarte');
      expect(eingeklappt.length).toBe(4);
      eingeklappt.forEach((karte) => {
        expect(karte.querySelector('.aufklapp-knopf')?.getAttribute('aria-expanded')).toBe('false');
        expect(karte.querySelector('.karte-inhalt, .karte-fuss, .karte-badges')).toBeNull();
      });
      expect(texte(seite, '.eingeklappte-karten .aufklapp-titel')).toEqual(['Titel k-3', 'Titel h-1', 'Titel b-1', 'Titel p-1']);
      expect(seite.querySelectorAll('.karte--schlicht').length).withContext('alle Karten schlicht').toBe(5);
    });

    it(`klappt eine Karte an Ort und Stelle auf und wieder zu, per Knopf mit aria-expanded (${wo})`, async () => {
      const seite = await oeffnen(mobil, GEMISCHT());
      const knopf = aufklapper(seite)[0];
      const karte = knopf.closest('app-beitragskarte')!;
      const koerperId = knopf.getAttribute('aria-controls')!;
      expect(knopf.tagName).toBe('BUTTON');
      expect(knopf.closest('h4')).withContext('Akkordeon: Knopf in der Ueberschrift').toBeTruthy();
      expect(document.getElementById(koerperId)?.hidden).toBeTrue();

      knopf.click();
      fixture.detectChanges();
      expect(knopf.getAttribute('aria-expanded')).toBe('true');
      const koerper = document.getElementById(koerperId)!;
      expect(koerper.hidden).toBeFalse();
      expect(karte.contains(koerper)).toBeTrue();
      expect(koerper.querySelector('.karte-inhalt')).toBeTruthy();
      expect(koerper.querySelector('.kopieren-knopf')).toBeTruthy();
      expect(aufklapper(seite).slice(1).every((k) => k.getAttribute('aria-expanded') === 'false'))
        .withContext('die anderen bleiben zu').toBeTrue();

      knopf.click();
      fixture.detectChanges();
      expect(knopf.getAttribute('aria-expanded')).toBe('false');
      expect(karte.querySelector('.karte-inhalt')).toBeNull();
    });

    it(`zeigt Bilder aus image_search_results (${wo})`, async () => {
      const seite = await oeffnen(mobil, GEMISCHT());
      seite.querySelector<HTMLButtonElement>('.weitere-umschalter')!.click();
      fixture.detectChanges();
      const bilder = seite.querySelectorAll('[data-typ="image"]');
      expect(bilder.length).withContext('in der erkannten und der anderen Gruppe').toBe(2);
      expect(text(bilder[0])).toContain('Titel b-1');
      bilder[0].querySelector<HTMLButtonElement>('.aufklapp-knopf')!.click();
      fixture.detectChanges();
      expect(bilder[0].querySelector('img')).withContext('eigenes Bild nach dem Aufklappen sichtbar').toBeTruthy();
    });

    it(`zeigt die Karten in einer Spalte ohne Grund und Rahmen (${wo})`, async () => {
      const seite = await oeffnen(mobil, GEMISCHT());
      const listen = Array.from(seite.querySelectorAll('.typ-block app-kartenliste ul'));
      expect(listen.length).toBeGreaterThan(0);
      listen.forEach((liste) => {
        expect(liste.classList).toContain('kartenliste--schlicht');
        expect(liste.classList).not.toContain('kartenliste--spalten');
      });
    });

    it(`zeigt keine Typ-Chips und oben kein "Antworten" (${wo})`, async () => {
      const seite = await oeffnen(mobil, antwort({ k: [erkannt('commentary', 'k-1', 0.9)], b: [erkannt('image', 'b-1', 0.8), erkannt('image', 'b-2', 0.7)] }));
      expect(seite.querySelector('.typ-leiste, .typ-chips, .typ-chip')).toBeNull();
      expect(seite.querySelector('.kopfband')).withContext('kein Kopfband mehr').toBeNull();
      expect(texte(seite, '.typ-ueberschrift')).toEqual(['Beste Antwort', 'Bilder · 2']);
    });
  }

  it('zeigt immer alle Typen', async () => {
    const seite = await oeffnen(false, GEMISCHT());
    expect(Array.from(seite.querySelector('.gruppe')!.querySelectorAll('.typ-block')).map((b) => b.getAttribute('data-typ')))
      .toEqual(['commentary', 'generictext', 'image', 'post']);
  });

  it('zeigt je Typ hoechstens drei Karten, auf Wunsch alle, und setzt den Fokus auf die erste neue', async () => {
    const kommentare = [1, 2, 3, 4, 5].map((n) => erkannt('commentary', `k-${n}`, 1 - n / 10));
    const seite = await oeffnen(false, antwort({ k: kommentare }));
    const block = () => seite.querySelector('[data-typ="commentary"]')!;
    expect(block().querySelectorAll('app-beitragskarte').length).toBe(3);
    const knopf = block().querySelector<HTMLButtonElement>('.alle-zeigen')!;
    expect(text(knopf)).toBe('Alle 4 weiteren Antworten zeigen');

    knopf.click();
    fixture.detectChanges();

    const karten = block().querySelectorAll('app-beitragskarte');
    expect(karten.length).toBe(5);
    expect(block().querySelector('.alle-zeigen')).toBeNull();
    expect(karten[3].contains(document.activeElement)).withContext('Fokus auf der vierten Karte').toBeTrue();
  });

  describe('Desktop ab 1024 px: fuenf Antworten offen (Maintainer 18.11.)', () => {
    const neun = () => [1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => erkannt('commentary', `k-${n}`, 1 - n / 100));
    const titel = (seite: Element, selektor: string) =>
      texte(seite, selektor === '.offene-karten' ? `${selektor} .karte-titel` : `${selektor} .aufklapp-titel`);

    it('zeigt die beste und vier weitere offen mit Kopieren, dann eingeklappte; Fokus nach "Alle zeigen"', async () => {
      const seite = await oeffnen(false, antwort({ k: neun(), h: [erkannt('generictext', 'h-1', 0.5)] }), AEHNLICH, true);
      const block = () => seite.querySelector('[data-typ="commentary"]')!;
      const offene = block().querySelectorAll('.offene-karten app-beitragskarte');
      expect(titel(block(), '.offene-karten')).toEqual(['Titel k-2', 'Titel k-3', 'Titel k-4', 'Titel k-5']);
      offene.forEach((karte) => {
        expect(karte.querySelector('.aufklapp-knopf')).toBeNull();
        expect(karte.querySelector('.kopieren-knopf')).toBeTruthy();
      });
      expect(titel(block(), '.eingeklappte-karten')).toEqual(['Titel k-6', 'Titel k-7']);
      // Lesereihenfolge: beste, Kasten, offene, eingeklappte
      const kasten = block().querySelector('app-zu-dieser-antwort')!;
      expect(kasten.compareDocumentPosition(offene[0]) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
      expect(seite.querySelector('[data-typ="generictext"] .offene-karten')).withContext('andere Typen wie bisher').toBeNull();

      const knopf = block().querySelector<HTMLButtonElement>('.alle-zeigen')!;
      expect(text(knopf)).toBe('Alle 4 weiteren Antworten zeigen');
      knopf.click();
      fixture.detectChanges();
      const karten = block().querySelectorAll('app-beitragskarte');
      expect(karten.length).toBe(9);
      expect(karten[7].contains(document.activeElement)).withContext('Fokus auf der achten Karte').toBeTrue();
    });

    it('zeigt bei weniger als fuenf Antworten alle offen', async () => {
      const drei = [1, 2, 3].map((n) => erkannt('commentary', `k-${n}`, 1 - n / 100));
      const seite = await oeffnen(false, antwort({ k: drei }), AEHNLICH, true);
      expect(titel(seite, '.offene-karten')).toEqual(['Titel k-2', 'Titel k-3']);
      expect(seite.querySelector('[data-typ="commentary"] .eingeklappte-karten, .alle-zeigen')).toBeNull();
    });

    it('baut beim Wechsel der Breite um und behaelt "Alle zeigen"', async () => {
      const seite = await oeffnen(false, antwort({ k: neun() }), AEHNLICH, false);
      expect(seite.querySelector('.offene-karten')).withContext('unter 1024 px nur die beste offen').toBeNull();
      expect(seite.querySelectorAll('.eingeklappte-karten app-beitragskarte').length).toBe(2);

      breit.next(true);
      neuZeichnen();
      expect(seite.querySelectorAll('.offene-karten app-beitragskarte').length).toBe(4);
      expect(seite.querySelectorAll('.eingeklappte-karten app-beitragskarte').length).toBe(2);

      seite.querySelector<HTMLButtonElement>('.alle-zeigen')!.click();
      fixture.detectChanges();
      breit.next(false);
      neuZeichnen();
      expect(seite.querySelector('.offene-karten')).toBeNull();
      expect(seite.querySelectorAll('.eingeklappte-karten app-beitragskarte').length).withContext('aufgeklappt bleibt aufgeklappt').toBe(8);
      expect(seite.querySelector('.alle-zeigen')).toBeNull();
    });
  });

  for (const mobil of [false, true]) {
    it(`nennt die erkannte Aussage in einer Zeile vor den Treffern; "Nicht gemeint?" klappt die Alternativen auf (${mobil ? 'Handy' : 'Desktop'})`, async () => {
      const seite = await oeffnen(mobil, GEMISCHT());
      const zeile = seite.querySelector('.erkannt-zeile')!;
      expect(text(zeile.querySelector('.erkannt-text'))).toContain(`Erkannt als „${ERKANNT}“`);
      expect(zeile.compareDocumentPosition(seite.querySelector('.gruppe')!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

      const umschalter = zeile.querySelector<HTMLButtonElement>('.erkannt-umschalter')!;
      expect(text(umschalter)).toContain('Nicht gemeint?');
      expect(umschalter.getAttribute('aria-expanded')).toBe('false');
      expect(umschalter.getAttribute('aria-controls')).toBe('erkannt-liste');
      expect(seite.querySelector<HTMLElement>('#erkannt-liste')!.hidden).toBeTrue();

      umschalter.click();
      fixture.detectChanges();

      expect(umschalter.getAttribute('aria-expanded')).toBe('true');
      expect(seite.querySelector<HTMLElement>('#erkannt-liste')!.hidden).toBeFalse();
      expect(texte(seite, '.erkannt-liste a')).toEqual(AEHNLICH.map((a) => a.text));
    });
  }

  it('sucht mit einem Klick auf eine Alternative unter "Nicht gemeint?" nach ihr', fakeAsync(async () => {
    const seite = await oeffnen(false, GEMISCHT());
    seite.querySelector<HTMLAnchorElement>('.erkannt-liste a')!.click();
    tick();
    expect(router.url).toBe('/result?searchQuery=Windr%C3%A4der%20sind%20zu%20laut');
  }));

  it('behaelt die Karten anderer Gruppen, wenn eine Gruppe aufklappt', async () => {
    // Vier Kommentare zur erkannten Aussage (eine Gruppe mit "Alle 4 … zeigen"), einer zu einer anderen.
    const viele = [1, 2, 3, 4].map((n) => erkannt('commentary', `k-${n}`, 0.9 - n / 100));
    const seite = await oeffnen(false, antwort({ k: [...viele, andere('commentary', 'a-1', 0.5)] }));
    const gruppen = () => seite.querySelectorAll('.gruppe');
    seite.querySelector<HTMLButtonElement>('.weitere-umschalter')!.click();
    fixture.detectChanges();
    const karteDerAnderen = gruppen()[1].querySelector('app-beitragskarte')!;

    gruppen()[0].querySelector<HTMLButtonElement>('.alle-zeigen')!.click();
    fixture.detectChanges();
    expect(gruppen()[0].querySelectorAll('app-beitragskarte').length).toBe(4);
    expect(gruppen()[1].querySelector('app-beitragskarte')).withContext('dieselbe Karte, Zustand bleibt').toBe(karteDerAnderen);
  });

  it('behaelt die gewaehlte Fassung einer Karte ueber den Themenfilter hinweg', async () => {
    const mitThema = (id: string, thema: { schluessel: string; name: string }) => {
      const t = erkannt('commentary', id, 0.9);
      t.themen = [thema];
      Object.assign(t.commentary_result, { short_text: 'Kurz', long_text: 'Eine lange Fassung' });
      return t;
    };
    const seite = await oeffnen(false, antwort({
      k: [mitThema('k-1', { schluessel: 'klima', name: 'Klima' }), mitThema('k-2', { schluessel: 'verkehr', name: 'Verkehr' })],
    }));
    const karte = () =>
      fixture.debugElement
        .queryAll(By.directive(BeitragskarteComponent))
        .map((d) => d.componentInstance as BeitragskarteComponent)
        .find((k) => k.daten.id === 'k-1')!;
    const vorher = karte();
    vorher.fassungWaehlen('lang');
    const thema = (name: string) =>
      Array.from(seite.querySelectorAll<HTMLButtonElement>('app-themen-filter button')).find((b) => text(b) === name)!;

    thema('Klima').click();
    fixture.detectChanges();
    thema('Alle Themen').click();
    fixture.detectChanges();

    expect(karte()).withContext('dieselbe Karte').toBe(vorher);
    expect(karte().gewaehlteFassung).toBe('lang');
  });

  it('setzt die Kartentitel unter Gruppe (h2) und Typ (h3) als h4 und behaelt die Aussage fuer Admins', async () => {
    const seite = await oeffnen(false, GEMISCHT());
    expect(seite.querySelectorAll('.typ-block h4.karte-titel').length).toBe(seite.querySelectorAll('.typ-block app-beitragskarte').length);
    expect(seite.querySelector('.typ-block h3.karte-titel')).toBeNull();
    const karte = fixture.componentInstance.ansicht[0].bloecke[0].karten[0];
    expect(karte.statement?.text).toBe(ERKANNT);
  });

  it('bietet "Hintergrundinfo ergänzen" an, wenn unter den Treffern keine Hintergrundinfo ist', fakeAsync(async () => {
    let seite = await oeffnen(false, antwort({ k: [erkannt('commentary', 'k-1', 0.9)] }));
    const navigieren = spyOn(router, 'navigate').and.resolveTo(true);
    const link = seite.querySelector<HTMLButtonElement>('.nicht-dabei-unten .hintergrund-ergaenzen')!;
    expect(text(link)).toBe('Hintergrundinfo ergänzen');
    link.click();
    expect(navigieren.calls.mostRecent().args[0]).toEqual(['/workflow/add-generictext']);

    TestBed.resetTestingModule();
    seite = await oeffnen(false, GEMISCHT());
    expect(seite.querySelector('.hintergrund-ergaenzen')).withContext('mit Hintergrundinfos nicht').toBeNull();
  }));

  it('vergisst die Alternativen der vorigen Suche', async () => {
    await oeffnen(false, GEMISCHT());
    fixture.componentInstance.alternativenOffen = true;
    expect(fixture.componentInstance.alternativen.length).toBe(2);

    TestBed.inject(StateManagementService).setSearchResults(antwort({ k: [erkannt('commentary', 'k-9', 0.9)] }));
    expect(fixture.componentInstance.alternativen).toEqual([]);
    expect(fixture.componentInstance.alternativenOffen).toBeFalse();
  });

  /**
   * Persona-Test 13.11.: Unter "Heizung verbieten" standen "Fleisch verbieten" und
   * "Gendern" als aehnliche Aussagen, die Chips zeigten "Kommentare 8" bei 2 passenden.
   * Werte wie aus dem lokalen Stack (Statement-Score gewichtet, Relevanz 0,7/1,0).
   */
  it('zeigt bei "Heizung verbieten" nur die erkannte Aussage offen; Fleisch, Gendern und direkte Treffer eingeklappt und nicht gezaehlt', async () => {
    const HEIZUNG = { id: 'h-aussage', text: 'Die Grünen wollen mir meine Heizung verbieten!' };
    const FLEISCH = { id: 'f-aussage', text: 'Die Grünen wollen uns das Fleisch verbieten!' };
    const GENDERN = { id: 'g-aussage', text: 'Die Grünen wollen uns das Gendern aufzwingen!' };
    const zu = (a: { id: string; text: string }, id: string, score: number) => treffer('commentary', id, a.id, a.text, score);
    const bdew = zu(HEIZUNG, 'bdew', 0.998);
    bdew.commentary_result.references = [{ reference_id: 'r-1', reference_text: 'https://www.bdew.de/', reference_description: 'BDEW' }];
    const seite = await oeffnen(true, antwort({
      k: [
        zu(HEIZUNG, 'testtext', 1.088), bdew, zu(HEIZUNG, 'energieberatung', 0.998),
        zu(FLEISCH, 'teller', 0.917), zu(FLEISCH, 'hof', 0.917),
        zu(GENDERN, 'privat', 0.862), zu(GENDERN, 'lohn', 0.862),
        direkt('commentary', 'solar', 0.575),
      ],
    }));

    expect(texte(seite, '.gruppe > h2 .gruppe-label')).toEqual([`Zu dieser Aussage: „${HEIZUNG.text}“`]);
    const offen = Array.from(seite.querySelectorAll('.gruppe app-beitragskarte')).map((k) => text(k));
    expect(offen.length).toBe(3);
    expect(offen.some((t) => t.includes('Titel bdew'))).withContext('beste Karte mit Herkunft steht oben').toBeTrue();
    expect(text(seite)).not.toContain('Fleisch verbieten');
    expect(text(seite.querySelector('.weitere-umschalter'))).toContain('Weitere, weniger passende Treffer (5)');

    seite.querySelector<HTMLButtonElement>('.weitere-umschalter')!.click();
    fixture.detectChanges();
    expect(texte(seite, '.gruppe > h2 .gruppe-aussage')).toEqual([`„${FLEISCH.text}“`, `„${GENDERN.text}“`]);
    expect(text(seite.querySelector('.beste-antwort'))).withContext('die beste bleibt die der erkannten Aussage').toContain('Titel testtext');
  });

  it('klappt ohne erkannte Aussage keine Gruppe ein; nur Bilder zur erkannten Aussage: die beste ist ein Bild', async () => {
    let seite = await oeffnen(false, antwort({
      k: [
        treffer('commentary', 'k-1', 'a', 'Aussage A', 0.9),
        treffer('commentary', 'k-2', 'b', 'Aussage B', 0.8),
        treffer('commentary', 'k-3', 'b', 'Aussage B', 0.7),
        treffer('commentary', 'k-4', 'c', 'Aussage C', 0.6),
      ],
    }));
    expect(seite.querySelector('.weitere')).toBeNull();
    expect(seite.querySelectorAll('.gruppe').length).toBe(3);

    expect(seite.querySelectorAll('.beste-antwort app-beitragskarte').length).withContext('nur die erste Gruppe hat eine beste').toBe(1);
    expect(texte(seite, '.weitere-ueberschrift')).toEqual(['Kommentare · 2', 'Kommentar · 1']);

    // Erkannte Aussage nur mit Bildern, der einzige Kommentar ist eingeklappt (weniger passend).
    TestBed.resetTestingModule();
    seite = await oeffnen(false, antwort({
      k: [andere('commentary', 'a-1', 0.5)],
      b: [erkannt('image', 'b-1', 0.9), erkannt('image', 'b-2', 0.85)],
    }));
    expect(text(seite.querySelector('.beste-antwort'))).toContain('Titel b-1');
    expect(texte(seite.querySelector('.gruppe')!, '.typ-ueberschrift')).toEqual(['Beste Antwort', 'Weitere Bilder · 1']);
    expect(seite.querySelector('.weitere-umschalter')).not.toBeNull();
  });

  it('bietet eingeklappte Aussagen unter "Nicht gemeint?" an und nur Themen der offenen Gruppe', async () => {
    const KLIMA = { schluessel: 'klima', name: 'Klima' };
    const ERNAEHRUNG = { schluessel: 'ernaehrung', name: 'Ernährung' };
    const mitThema = (t: any, thema: { schluessel: string; name: string }) => ({ ...t, themen: [thema] });
    const anderAlsAlternative = { id: ANDERE_ID, text: ANDERE, replysuggestions_count: 2, score: 0.9 };
    const seite = await oeffnen(false, antwort({
      k: [
        mitThema(erkannt('commentary', 'k-1', 0.9), KLIMA),
        mitThema(erkannt('commentary', 'k-2', 0.85), KLIMA),
        mitThema(andere('commentary', 'a-1', 0.8), ERNAEHRUNG),
      ],
    }), [anderAlsAlternative, ...AEHNLICH]);

    expect(texte(seite, '.erkannt-liste a')).withContext('eingeklappte Aussage waehlbar').toContain(ANDERE);
    const themen = texte(seite, 'app-themen-filter button');
    expect(themen).toEqual(['Alle Themen', 'Klima']);
    expect(themenDerTreffer(antwort({ k: [mitThema(andere('commentary', 'a-1', 0.8), ERNAEHRUNG)] }))
      .map((t) => t.schluessel)).withContext('ohne erkannte Aussage alle Themen').toEqual(['ernaehrung']);

    Array.from(seite.querySelectorAll<HTMLButtonElement>('app-themen-filter button')).find((b) => text(b) === 'Klima')!.click();
    fixture.detectChanges();
    expect(texte(seite, '.gruppe > h2 .gruppe-label')).toEqual([`Zu dieser Aussage: „${ERKANNT}“`]);
    expect(seite.querySelector('.weitere')).withContext('Ernaehrung faellt mit dem Thema weg').toBeNull();
  });

  it('verknuepft den Knopf "Weitere, weniger passende Treffer" nur offen mit der Liste', async () => {
    const seite = await oeffnen(false, GEMISCHT());
    const knopf = seite.querySelector<HTMLButtonElement>('.weitere-umschalter')!;
    expect(knopf.getAttribute('aria-controls')).toBeNull();
    knopf.click();
    fixture.detectChanges();
    expect(knopf.getAttribute('aria-controls')).toBe('weitere-treffer');
    expect(seite.querySelector('#weitere-treffer')).toBeTruthy();
  });

  it('zeigt "Nicht gemeint?" nicht ohne Alternativen', async () => {
    const seite = await oeffnen(false, GEMISCHT(), []);
    expect(text(seite.querySelector('.erkannt-text'))).toContain('Erkannt als');
    expect(seite.querySelector('.erkannt-umschalter, .erkannt-liste')).toBeNull();
  });

  it('nennt keine erkannte Aussage, wenn kein Treffer ueber eine Aussage kam, und eine Gruppe fuer die direkten Treffer', async () => {
    const seite = await oeffnen(false, antwort({ k: [direkt('commentary', 'k-1', 0.6)] }));
    expect(text(seite.querySelector('.erkannt-zeile'))).not.toContain('Erkannt als');
    expect(texte(seite, '.gruppe > h2 .gruppe-label')).toEqual(['Passt zu deinem Suchtext']);
  });

  describe('Ergebnis teilen (B7)', () => {
    // Mit erkannter Aussage geht sie in den Link, nicht der rohe Suchtext (Review zu #675)
    const LINK = `${window.location.origin}/result?searchQuery=${encodeURIComponent(ERKANNT)}`;

    for (const mobil of [false, true]) {
      it(`steht als Symbol in der Zeile "Erkannt als", mit der erkannten Aussage im Namen (${mobil ? 'Handy' : 'Desktop'})`, async () => {
        const seite = await oeffnen(mobil, GEMISCHT());
        const knopf = seite.querySelector<HTMLButtonElement>('.erkannt-zeile .ergebnis-teilen-symbol')!;
        expect(knopf.tagName).toBe('BUTTON');
        expect(text(knopf)).toBe('share');
        expect(knopf.getAttribute('aria-label')).toBe(`Ergebnis teilen: Antworten auf „${ERKANNT}“`);
        expect(seite.querySelectorAll('.ergebnis-teilen-symbol').length).toBe(1);
      });
    }

    it('oeffnet das Teilen-Menue mit dem Link auf die erkannte Aussage und zaehlt keine Nutzung', async () => {
      const seite = await oeffnen(true, GEMISCHT());
      nav.share = jasmine.createSpy('share').and.resolveTo(undefined);

      seite.querySelector<HTMLButtonElement>('.ergebnis-teilen-symbol')!.click();
      await fixture.whenStable();

      expect(nav.share).toHaveBeenCalledOnceWith({ url: LINK, text: `Antworten auf: „${ERKANNT}“` });
      TestBed.inject(HttpTestingController).expectNone((r) => r.url.includes('/usage'));
    });

    it('kopiert am Desktop den Link und sagt es', async () => {
      await oeffnen(false, GEMISCHT());
      const kopieren = spyOn(TestBed.inject(Clipboard), 'copy').and.returnValue(true);
      const snack = spyOn(TestBed.inject(MatSnackBar), 'open');

      await fixture.componentInstance.ergebnisTeilen();

      expect(kopieren).toHaveBeenCalledOnceWith(LINK);
      expect(snack.calls.mostRecent().args[0]).toBe(TEILEN_LINK_KOPIERT);
    });

    it('meldet nichts, wenn das Teilen abgebrochen wird', async () => {
      await oeffnen(true, GEMISCHT());
      nav.share = jasmine.createSpy('share').and.rejectWith(new DOMException('abgebrochen', 'AbortError'));
      const kopieren = spyOn(TestBed.inject(Clipboard), 'copy');
      const snack = spyOn(TestBed.inject(MatSnackBar), 'open');

      await fixture.componentInstance.ergebnisTeilen();

      expect(kopieren).not.toHaveBeenCalled();
      expect(snack).not.toHaveBeenCalled();
    });

    it('steht ohne erkannte Aussage oben ueber den Treffern und nennt den Suchtext', async () => {
      const seite = await oeffnen(false, antwort({ k: [direkt('commentary', 'k-1', 0.6)] }));
      const knopf = seite.querySelector<HTMLButtonElement>('.erkannt-zeile .ergebnis-teilen-symbol')!;
      expect(knopf.getAttribute('aria-label')).toBe('Ergebnis teilen: Antworten auf „windraeder voegel“');
      expect(knopf.compareDocumentPosition(seite.querySelector('.gruppe')!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    });

    it('gibt ohne erkannte Aussage den Suchtext nur gekuerzt weiter', async () => {
      await oeffnen(true, antwort({ k: [direkt('commentary', 'k-1', 0.6)] }));
      const eingefuegt = 'Ein langer fremder Post von Erika Musterfrau ' + 'mit sehr vielen Worten '.repeat(20);
      fixture.componentInstance.searchQuery = eingefuegt;
      nav.share = jasmine.createSpy('share').and.resolveTo(undefined);

      await fixture.componentInstance.ergebnisTeilen();

      const geteilt = (nav.share as jasmine.Spy).calls.mostRecent().args[0] as ShareData;
      const suchtext = new URL(geteilt.url!).searchParams.get('searchQuery')!;
      expect(suchtext.length).toBeLessThanOrEqual(200);
      expect(eingefuegt.startsWith(suchtext)).toBeTrue();
      expect(geteilt.text).toBe(`Antworten auf: „${suchtext}“`);
    });
  });

  it('nennt ohne erkannte Aussage jede Aussage in ihrer Gruppe', async () => {
    // Je ein Treffer zu drei Aussagen: keine traegt Mehrheit und obersten Treffer zugleich.
    const seite = await oeffnen(false, antwort({
      k: [
        treffer('commentary', 'k-1', 'a', 'Aussage A', 0.9),
        treffer('commentary', 'k-2', 'b', 'Aussage B', 0.8),
        treffer('commentary', 'k-3', 'b', 'Aussage B', 0.7),
        treffer('commentary', 'k-4', 'c', 'Aussage C', 0.6),
      ],
    }));
    expect(seite.querySelector('.erkannt-aussage')).toBeNull();
    expect(texte(seite, '.gruppe > h2 .gruppe-aussage')).toEqual(['„Aussage A“', '„Aussage B“', '„Aussage C“']);
    expect(texte(seite, '.gruppe > h2 .gruppe-label')).toEqual(['Zur Aussage:', 'Zur Aussage:', 'Zur Aussage:']);
  });

  it('zeigt Treffer, auch wenn nur Posts oder nur Bilder passen', async () => {
    let seite = await oeffnen(false, antwort({ p: [direkt('post', 'p-1', 0.6)] }));
    expect(seite.querySelector('.unified-empty-state')).toBeNull();
    expect(texte(seite, '.typ-ueberschrift')).toEqual(['Beste Antwort']);
    expect(text(seite.querySelector('.beste-antwort'))).toContain('Titel p-1');

    TestBed.resetTestingModule();
    seite = await oeffnen(true, antwort({ b: [erkannt('image', 'b-1', 0.6)] }));
    expect(seite.querySelector('.unified-empty-state')).toBeNull();
    expect(text(seite.querySelector('.beste-antwort'))).toContain('Titel b-1');
  });

  it('fuehrt mit "Antworten" unter den Treffern ins Kommentarformular; oben steht keins', fakeAsync(async () => {
    const seite = await oeffnen(false, GEMISCHT());
    const navigieren = spyOn(router, 'navigate').and.resolveTo(true);
    expect(seite.querySelector('.typ-leiste')).toBeNull();

    const unten = () => seite.querySelector<HTMLButtonElement>('.nicht-dabei-unten .neu-anlegen-knopf button')!;
    expect(text(unten())).toContain('Antworten');
    unten().click();
    expect(navigieren.calls.mostRecent().args[0]).toEqual(['/workflow/add-commentary']);
  }));

  for (const mobil of [false, true]) {
    it(`antwortet mit "Antworten" auf die erkannte Aussage, nicht auf die der Suche (${mobil ? 'Handy' : 'Desktop'})`, async () => {
      // Die Suche hat eine eigene Aussage angelegt (11111111-...), die getById Nicht-Admins
      // nicht ausliefert (#436); gefunden wurde ueber die erkannte (#680).
      const seite = await oeffnen(mobil, GEMISCHT());
      const navigieren = spyOn(router, 'navigate').and.resolveTo(true);
      const erwartet = [['/workflow/add-commentary'], { queryParams: { aussage: ERKANNT_ID, searchQuery: 'windraeder voegel' } }];

      seite.querySelector<HTMLButtonElement>('.nicht-dabei-unten .neu-anlegen-knopf button')!.click();
      expect(navigieren.calls.mostRecent().args).toEqual(erwartet as any);
    });
  }

  it('antwortet ohne erkannte Aussage auf die der Suche', async () => {
    await oeffnen(false, antwort({ k: [direkt('commentary', 'k-1', 0.6)] }));
    const navigieren = spyOn(router, 'navigate').and.resolveTo(true);

    fixture.componentInstance.navigateToContribute('generictext');

    expect(navigieren).toHaveBeenCalledWith(['/workflow/add-generictext'], {
      queryParams: { aussage: '11111111-2222-4333-8444-555555555555', searchQuery: 'windraeder voegel' },
    });
  });

  it('zeigt unter den Treffern "Nicht dabei?" und danach den ruhigen Rat', async () => {
    const seite = await oeffnen(true, GEMISCHT());
    const unten = seite.querySelector('.nicht-dabei-unten')!;
    const rat = seite.querySelector('.keine-antwort-noetig')!;
    const letzteGruppe = Array.from(seite.querySelectorAll('.gruppe')).pop()!;
    expect(letzteGruppe.compareDocumentPosition(unten) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(unten.compareDocumentPosition(rat) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(text(unten)).toContain('Nicht dabei?');
    expect(text(rat)).toContain('Nicht jede Aussage braucht eine Antwort');
  });

  it('beginnt eine neue Suche zugeklappt und mit Themen der neuen Treffer', async () => {
    const kommentare = [1, 2, 3, 4].map((n) => erkannt('commentary', `k-${n}`, 1 - n / 10));
    const seite = await oeffnen(false, antwort({ k: kommentare }));
    seite.querySelector<HTMLButtonElement>('.alle-zeigen')!.click();
    fixture.detectChanges();
    expect(seite.querySelectorAll('app-beitragskarte').length).toBe(4);

    TestBed.inject(StateManagementService).setSearchResults(antwort({ k: kommentare.map((k) => ({ ...k })) }));
    neuZeichnen();
    expect(seite.querySelectorAll('app-beitragskarte').length).toBe(3);
  });
});
