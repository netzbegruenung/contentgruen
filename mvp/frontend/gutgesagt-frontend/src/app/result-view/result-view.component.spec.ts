import { ChangeDetectorRef } from '@angular/core';
import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { BreakpointObserver } from '@angular/cdk/layout';
import { of } from 'rxjs';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter, Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';

import { ResultViewComponent, aussagenDerTreffer, erkannteAussage } from './result-view.component';
import { TYPFILTER_SCHLUESSEL } from './ergebnis-gruppen';
import { AuthService } from '../auth/auth.service';
import { StatementService } from '../services/statement.service';
import { routes } from '../app.routes';
import { ohneWaechter } from '../testing/routen-ohne-waechter';
import { StateManagementService } from '../services/state-management.service';

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

    unten.querySelector<HTMLButtonElement>('.neu-anlegen-knopf button')!.click();
    tick();
    expect(router.url).toBe(`/workflow/add-commentary?aussage=${AUSSAGE_ID}&searchQuery=waermepumpe%20teuer`);
  }));

  it('sucht mit einem Klick auf eine aehnliche Aussage nach ihr', fakeAsync(() => {
    const seite = oeffnen(false, true);

    seite.querySelector<HTMLAnchorElement>('.nicht-dabei-unten .aehnliche-aussage')!.click();
    tick();
    expect(router.url).toBe('/result?searchQuery=W%C3%A4rmepumpen%20lohnen%20sich%20nicht');
  }));
});

describe('aussagenDerTreffer', () => {
  it('sammelt die Aussagen der Treffer und der Suche, jede einmal, ohne leere', () => {
    const treffer = (statement_id: string | null) => ({ score: 1, statement_text: '', statement_id }) as any;
    expect(
      aussagenDerTreffer({
        query_was_newly_added_as_statement: false,
        statement_id: 'a',
        statement_text: '',
        commentary_search_results_count: 2,
        commentary_search_results: [treffer('b'), treffer(null)],
        generictext_search_results_count: 1,
        generictext_search_results: [treffer('b')],
        post_search_results_count: 1,
        post_search_results: [treffer('c')],
        image_search_results_count: 1,
        image_search_results: [treffer('d')],
      }),
    ).toEqual(['a', 'b', 'd', 'c']);
  });
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
describe('ResultViewComponent: Kopfband, Chips und Gruppen je Aussage', () => {
  const ERKANNT_ID = '22222222-2222-4333-8444-555555555555';
  const ANDERE_ID = '44444444-2222-4333-8444-555555555555';
  const ERKANNT = 'Windräder töten die Vögel!';
  const ANDERE = 'Windkraft zerstört die Landschaft!';
  const AEHNLICH = [
    { id: '55555555-2222-4333-8444-555555555555', text: 'Windräder sind zu laut', replysuggestions_count: 1, score: 0.8 },
    { id: '66666666-2222-4333-8444-555555555555', text: 'Infraschall macht krank', replysuggestions_count: 0, score: 0.7 },
  ];
  const SAETZE = {
    commentary: 'Eine Antwort, die du direkt posten kannst.',
    generictext: 'Fakten und Zahlen, die eine Antwort stützen.',
    image: 'Ein Bild mit Unterschrift, das für sich spricht.',
    post: 'Ein gelungener Beitrag aus einem sozialen Netzwerk, zum Teilen.',
  };

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

  beforeEach(() => sessionStorage.removeItem(TYPFILTER_SCHLUESSEL));
  afterEach(() => sessionStorage.removeItem(TYPFILTER_SCHLUESSEL));

  async function oeffnen(mobil: boolean, suchantwort: any, aehnliche: any[] = AEHNLICH): Promise<HTMLElement> {
    const statementService = jasmine.createSpyObj('StatementService', ['aehnlicheAussagen']);
    statementService.aehnlicheAussagen.and.returnValue(of(aehnliche));
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
    TestBed.inject(StateManagementService).setSearchResults(suchantwort);
    fixture = TestBed.createComponent(ResultViewComponent);
    fixture.detectChanges();
    fixture.componentInstance.searchQuery = 'windraeder voegel';
    fixture.debugElement.injector.get(ChangeDetectorRef).markForCheck();
    fixture.detectChanges();
    // Die aehnlichen Aussagen fuers Kopfband kommen nach der Pruefung an (Promise).
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

  function chip(seite: HTMLElement, name: string): HTMLButtonElement {
    return Array.from(seite.querySelectorAll<HTMLButtonElement>('.typ-chip')).find((c) => text(c).startsWith(name))!;
  }

  for (const mobil of [false, true]) {
    const wo = mobil ? 'Handy' : 'Desktop';

    it(`gruppiert nach Aussage: erkannte zuerst, aehnliche danach, direkte Treffer zuletzt (${wo})`, async () => {
      const seite = await oeffnen(mobil, GEMISCHT());
      // So, wie ein Screenreader die Ueberschrift liest: ohne das Symbol, mit Leerzeichen.
      const ueberschriften = Array.from(seite.querySelectorAll('.gruppe > h2')).map((h) => {
        const kopie = h.cloneNode(true) as HTMLElement;
        kopie.querySelectorAll('[aria-hidden="true"]').forEach((e) => e.remove());
        return (kopie.textContent ?? '').replace(/\s+/g, ' ').trim();
      });
      expect(ueberschriften).toEqual([
        'Zu dieser Aussage 5 Treffer',
        `Zu einer ähnlichen Aussage: „${ANDERE}“ 2 Treffer`,
        'Passt zu deinem Suchtext 1 Treffer',
      ]);
      expect(seite.querySelector('.mobile-tab-bar, app-result-carousel')).withContext('keine Tabs, kein Karussell').toBeNull();
    });

    it(`zeigt an den Karten keine eigene Antwort-auf-Zeile, die Gruppe traegt die Aussage (${wo})`, async () => {
      const seite = await oeffnen(mobil, GEMISCHT());
      expect(seite.querySelectorAll('app-beitragskarte').length).toBe(8);
      expect(seite.querySelector('.statement-zeile, .statement-vorschau')).toBeNull();
    });

    it(`ordnet die Typen je Gruppe fest und erklaert jeden Typ einmal (${wo})`, async () => {
      const seite = await oeffnen(mobil, GEMISCHT());
      const ersteGruppe = seite.querySelector('.gruppe')!;
      expect(Array.from(ersteGruppe.querySelectorAll('.typ-block')).map((b) => b.getAttribute('data-typ')))
        .toEqual(['commentary', 'generictext', 'image', 'post']);
      expect(texte(ersteGruppe, '.typ-ueberschrift')).toEqual(['Kommentare', 'Hintergrundinfo', 'Bild', 'Post']);
      expect(texte(seite, '.typ-erklaerung')).toEqual([SAETZE.commentary, SAETZE.generictext, SAETZE.image, SAETZE.post]);
    });

    it(`zeigt Bilder aus image_search_results (${wo})`, async () => {
      const seite = await oeffnen(mobil, GEMISCHT());
      const bilder = seite.querySelectorAll('[data-typ="image"]');
      expect(bilder.length).withContext('in der erkannten und der aehnlichen Gruppe').toBe(2);
      expect(text(bilder[0])).toContain('Titel b-1');
      expect(bilder[0].querySelector('img')).withContext('eigenes Bild direkt sichtbar').toBeTruthy();
    });

    it(`zeigt die Karten ab 600 px als Raster (${wo})`, async () => {
      const seite = await oeffnen(mobil, GEMISCHT());
      const listen = seite.querySelectorAll('.typ-block app-kartenliste ul');
      expect(listen.length).toBe(seite.querySelectorAll('.typ-block').length);
      listen.forEach((liste) => expect(liste.classList).toContain('kartenliste--spalten'));
    });

    it(`bietet Chips nur fuer Typen mit Treffern, mit Zahl, "Alle" gewaehlt (${wo})`, async () => {
      const seite = await oeffnen(mobil, antwort({ k: [erkannt('commentary', 'k-1', 0.9)], b: [erkannt('image', 'b-1', 0.8), erkannt('image', 'b-2', 0.7)] }));
      expect(texte(seite, '.typ-chip')).toEqual(['Alle 3', 'Kommentare 1', 'Bilder 2']);
      expect(seite.querySelector('.typ-chips')?.getAttribute('role')).toBe('group');
      expect(chip(seite, 'Alle').getAttribute('aria-pressed')).toBe('true');
      expect(chip(seite, 'Bilder').getAttribute('aria-pressed')).toBe('false');
    });
  }

  it('filtert per Chip, sagt die Wahl an und merkt sie fuer die Sitzung', async () => {
    const seite = await oeffnen(false, GEMISCHT());

    chip(seite, 'Bilder').click();
    fixture.detectChanges();

    expect(chip(seite, 'Bilder').getAttribute('aria-pressed')).toBe('true');
    expect(chip(seite, 'Alle').getAttribute('aria-pressed')).toBe('false');
    expect(Array.from(seite.querySelectorAll('.typ-block')).map((b) => b.getAttribute('data-typ'))).toEqual(['image', 'image']);
    expect(texte(seite, '.gruppe > h2 .gruppe-zahl')).withContext('Zahl je Gruppe passt zum Filter').toEqual(['1 Treffer', '1 Treffer']);
    expect(text(seite.querySelector('.typ-ansage'))).toBe('Nur Bilder, 2 Treffer');
    expect(sessionStorage.getItem(TYPFILTER_SCHLUESSEL)).toBe('image');

    // Eine neue Ansicht in derselben Sitzung beginnt mit derselben Wahl.
    const zweite = TestBed.createComponent(ResultViewComponent);
    zweite.detectChanges();
    expect(zweite.componentInstance.typFilter).toBe('image');

    chip(seite, 'Alle').click();
    fixture.detectChanges();
    expect(text(seite.querySelector('.typ-ansage'))).toBe('Alle Typen, 8 Treffer');
    expect(sessionStorage.getItem(TYPFILTER_SCHLUESSEL)).toBeNull();
  });

  it('zeigt alle Typen, wenn der gemerkte Typ in dieser Suche keine Treffer hat', async () => {
    sessionStorage.setItem(TYPFILTER_SCHLUESSEL, 'post');
    const seite = await oeffnen(false, antwort({ k: [erkannt('commentary', 'k-1', 0.9)] }));
    expect(chip(seite, 'Alle').getAttribute('aria-pressed')).toBe('true');
    expect(seite.querySelectorAll('app-beitragskarte').length).toBe(1);
  });

  it('zeigt je Typ hoechstens drei Karten, auf Wunsch alle, und setzt den Fokus auf die erste neue', async () => {
    const kommentare = [1, 2, 3, 4, 5].map((n) => erkannt('commentary', `k-${n}`, 1 - n / 10));
    const seite = await oeffnen(false, antwort({ k: kommentare }));
    const block = () => seite.querySelector('[data-typ="commentary"]')!;
    expect(block().querySelectorAll('app-beitragskarte').length).toBe(3);
    const knopf = block().querySelector<HTMLButtonElement>('.alle-zeigen')!;
    expect(text(knopf)).toBe('Alle 5 Kommentare zeigen');

    knopf.click();
    fixture.detectChanges();

    const karten = block().querySelectorAll('app-beitragskarte');
    expect(karten.length).toBe(5);
    expect(block().querySelector('.alle-zeigen')).toBeNull();
    expect(karten[3].contains(document.activeElement)).withContext('Fokus auf der vierten Karte').toBeTrue();
  });

  it('zeigt am Desktop die erkannte Aussage im Kopfband, mit den Alternativen unter "Nicht gemeint?"', async () => {
    const seite = await oeffnen(false, GEMISCHT());
    expect(text(seite.querySelector('.kopfband-aussage'))).toBe(`„${ERKANNT}“`);
    expect(text(seite.querySelector('.kopfband-frage'))).toBe('Nicht gemeint?');
    expect(seite.querySelector('.kopfband-umschalter')).toBeNull();
    expect(texte(seite, '.kopfband-liste a')).toEqual(AEHNLICH.map((a) => a.text));
    // Das Kopfband steht vor den Chips und der ersten Gruppe.
    const band = seite.querySelector('.kopfband')!;
    expect(band.compareDocumentPosition(seite.querySelector('.typ-chips')!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('klappt am Handy die Alternativen erst mit "Nicht gemeint?" auf', async () => {
    const seite = await oeffnen(true, GEMISCHT());
    const umschalter = seite.querySelector<HTMLButtonElement>('.kopfband-umschalter')!;
    expect(text(umschalter)).toContain('Nicht gemeint?');
    expect(umschalter.getAttribute('aria-expanded')).toBe('false');
    expect(seite.querySelector('.kopfband-liste')).toBeNull();

    umschalter.click();
    fixture.detectChanges();

    expect(umschalter.getAttribute('aria-expanded')).toBe('true');
    expect(texte(seite, '.kopfband-liste a')).toEqual(AEHNLICH.map((a) => a.text));
  });

  it('sucht mit einem Klick auf eine Alternative im Kopfband nach ihr', fakeAsync(async () => {
    const seite = await oeffnen(false, GEMISCHT());
    seite.querySelector<HTMLAnchorElement>('.kopfband-liste a')!.click();
    tick();
    expect(router.url).toBe('/result?searchQuery=Windr%C3%A4der%20sind%20zu%20laut');
  }));

  it('zeigt "Nicht gemeint?" nicht ohne Alternativen', async () => {
    const seite = await oeffnen(false, GEMISCHT(), []);
    expect(seite.querySelector('.kopfband')).toBeTruthy();
    expect(seite.querySelector('.kopfband-alternativen')).toBeNull();
  });

  it('zeigt kein Kopfband, wenn kein Treffer ueber eine Aussage kam, und eine Gruppe fuer die direkten Treffer', async () => {
    const seite = await oeffnen(false, antwort({ k: [direkt('commentary', 'k-1', 0.6)] }));
    expect(seite.querySelector('.kopfband')).toBeNull();
    expect(texte(seite, '.gruppe > h2 .gruppe-label')).toEqual(['Passt zu deinem Suchtext']);
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
    expect(seite.querySelector('.kopfband')).toBeNull();
    expect(texte(seite, '.gruppe > h2 .gruppe-aussage')).toEqual(['„Aussage A“', '„Aussage B“', '„Aussage C“']);
    expect(texte(seite, '.gruppe > h2 .gruppe-label')).toEqual(['Zur Aussage:', 'Zur Aussage:', 'Zur Aussage:']);
  });

  it('zeigt Treffer, auch wenn nur Posts oder nur Bilder passen', async () => {
    let seite = await oeffnen(false, antwort({ p: [direkt('post', 'p-1', 0.6)] }));
    expect(seite.querySelector('.unified-empty-state')).toBeNull();
    expect(texte(seite, '.typ-chip')).toEqual(['Alle 1', 'Posts 1']);
    expect(text(seite)).toContain('Titel p-1');

    TestBed.resetTestingModule();
    seite = await oeffnen(true, antwort({ b: [erkannt('image', 'b-1', 0.6)] }));
    expect(seite.querySelector('.unified-empty-state')).toBeNull();
    expect(texte(seite, '.typ-chip')).toEqual(['Alle 1', 'Bilder 1']);
  });

  it('fuehrt mit "Antworten" oben und unten ins Kommentarformular, mit Hintergrund-Filter unten ins Hintergrundformular', fakeAsync(async () => {
    const seite = await oeffnen(false, GEMISCHT());
    const navigieren = spyOn(router, 'navigate').and.resolveTo(true);

    seite.querySelector<HTMLButtonElement>('.typ-leiste .ergaenzen-link')!.click();
    expect(navigieren.calls.mostRecent().args[0]).toEqual(['/workflow/add-commentary']);

    const unten = () => seite.querySelector<HTMLButtonElement>('.nicht-dabei-unten .neu-anlegen-knopf button')!;
    expect(text(unten())).toContain('Antworten');
    unten().click();
    expect(navigieren.calls.mostRecent().args[0]).toEqual(['/workflow/add-commentary']);

    chip(seite, 'Hintergrundinfos').click();
    fixture.detectChanges();
    expect(text(unten())).toContain('Hintergrundinfo ergänzen');
    unten().click();
    expect(navigieren.calls.mostRecent().args[0]).toEqual(['/workflow/add-generictext']);
  }));

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
