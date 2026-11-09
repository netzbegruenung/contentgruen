import { ChangeDetectorRef } from '@angular/core';
import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { BreakpointObserver } from '@angular/cdk/layout';
import { of } from 'rxjs';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter, Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';

import { ResultViewComponent, aussagenDerTreffer, erkannteAussage } from './result-view.component';
import { AuthService } from '../auth/auth.service';
import { StatementService } from '../services/statement.service';
import { routes } from '../app.routes';
import { ohneWaechter } from '../testing/routen-ohne-waechter';
import { StateManagementService } from '../services/state-management.service';

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

  it('fuehrt am Desktop in beide Formulare', fakeAsync(() => {
    oeffnen(false, AUSSAGE_ID);

    knopf('.action-buttons-top', 0).click();
    tick();
    expect(router.url).toBe(`/workflow/add-commentary?aussage=${AUSSAGE_ID}`);

    knopf('.action-buttons-top', 1).click();
    tick();
    expect(router.url).toBe(`/workflow/add-generictext?aussage=${AUSSAGE_ID}`);
  }));

  it('fuehrt am Handy ebenso dorthin', fakeAsync(() => {
    oeffnen(true, AUSSAGE_ID);

    knopf('.mobile-action-buttons', 0).click();
    tick();
    expect(router.url).toBe(`/workflow/add-commentary?aussage=${AUSSAGE_ID}`);
  }));

  it('bietet am Handy auch mit Treffern das Ergaenzen an, unter dem Suchband und unter der Liste', fakeAsync(() => {
    oeffnen(true, AUSSAGE_ID);
    const komponente = fixture.componentInstance;
    komponente.hasCommentaryResults = true;
    komponente.currentSection = 'commentary';
    // OnPush: die Flags von aussen gesetzt, also selbst zur Pruefung vormerken.
    fixture.debugElement.injector.get(ChangeDetectorRef).markForCheck();
    fixture.detectChanges();

    const oben: HTMLButtonElement = fixture.nativeElement.querySelector('.mobile-ergaenzen-kopf button');
    const unten: HTMLButtonElement = fixture.nativeElement.querySelector('.mobile-ergaenzen button');
    expect(oben.textContent!.trim()).toBe('Selbst beantworten');
    expect(unten.textContent).toContain('Selbst beantworten');
    expect(fixture.nativeElement.querySelector('.mobile-ergaenzen app-nicht-dabei').textContent).toContain('Nicht dabei?');
    expect(fixture.nativeElement.querySelector('.mobile-empty-state')).toBeNull();

    unten.click();
    tick();
    expect(router.url).toBe(`/workflow/add-commentary?aussage=${AUSSAGE_ID}`);

    komponente.hasGenerictextResults = true;
    komponente.currentSection = 'generictext';
    fixture.debugElement.injector.get(ChangeDetectorRef).markForCheck();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.mobile-ergaenzen button').textContent).toContain('Hintergrundinfo ergänzen');
  }));

  it('zeigt am Handy den leeren Reiter Hintergrund (0) waehlbar, mit einem Satz zum Ergaenzen (#599)', fakeAsync(() => {
    oeffnen(true, AUSSAGE_ID);
    const komponente = fixture.componentInstance;
    komponente.hasCommentaryResults = true;
    komponente.currentSection = 'commentary';
    fixture.debugElement.injector.get(ChangeDetectorRef).markForCheck();
    fixture.detectChanges();

    const reiter: HTMLButtonElement[] = Array.from(fixture.nativeElement.querySelectorAll('.mobile-tab-bar .tab-button'));
    const hintergrund = reiter.find((r) => r.textContent!.includes('Hintergrund'))!;
    expect(hintergrund.disabled).toBeFalse();
    expect(hintergrund.textContent).toContain('(0)');

    hintergrund.click();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.reiter-leer').textContent).toContain('noch keine Hintergrundinfo');
    expect(fixture.nativeElement.querySelector('.mobile-ergaenzen button').textContent).toContain('Hintergrundinfo ergänzen');
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

describe('ResultViewComponent: Posts in der Suche', () => {
  let fixture: ComponentFixture<ResultViewComponent>;

  const POST = {
    score: 0.9,
    statement_text: '',
    statement_similarity_score: 0,
    reply_relevance: 0,
    post_result: {
      id: 'p-1',
      content_type: 'post',
      title: 'Ein Reel, das Wärmepumpen erklärt',
      text: 'Worum es geht',
      platform: 'Instagram',
      author: '@klimaverein',
      url: 'https://www.instagram.com/p/abc/',
      engagement: 0,
      references: [],
    },
  };

  function oeffnen(mobil: boolean, mitKommentar = false): void {
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
      statement_text: 'waermepumpe',
      commentary_search_results_count: mitKommentar ? 1 : 0,
      commentary_search_results: mitKommentar
        ? [{ ...POST, post_result: undefined, commentary_result: { ...POST.post_result, id: 'k-1', content_type: 'commentary', title: 'Ein Kommentar' } } as any]
        : [],
      generictext_search_results_count: 0,
      generictext_search_results: [],
      post_search_results_count: 1,
      post_search_results: [POST as any],
    });
    fixture = TestBed.createComponent(ResultViewComponent);
    fixture.detectChanges();
  }

  it('zeigt am Handy einen Post-Tab und oeffnet ihn, wenn nur Posts passen', () => {
    oeffnen(true);
    const seite: HTMLElement = fixture.nativeElement;

    expect(seite.querySelector('.mobile-empty-state')).toBeNull();
    expect(seite.querySelector('.tab-post')?.classList).toContain('active');
    expect(seite.querySelector('.mobile-section')?.textContent).toContain('Ein Reel, das Wärmepumpen erklärt');
  });

  it('bleibt am Handy beim Kommentar-Tab, wenn es auch Kommentare gibt', () => {
    oeffnen(true, true);

    expect(fixture.componentInstance.currentSection).toBe('commentary');
    expect(fixture.nativeElement.querySelector('.tab-post')).toBeTruthy();
  });

  it('zeigt am Desktop einen Abschnitt mit den Posts statt des Leerzustands', () => {
    oeffnen(false);
    const seite: HTMLElement = fixture.nativeElement;

    expect(seite.querySelector('.unified-empty-state')).toBeNull();
    expect(seite.querySelector('.post-anzahl')?.textContent).toContain('1 passender Post gefunden.');
    expect(seite.textContent).toContain('Ein Reel, das Wärmepumpen erklärt');
  });
});

/**
 * Nutzertest: Was ein Kommentar und was eine Hintergrundinfo ist, war auf der
 * Ergebnisseite nicht klar. Je eine Erklaerzeile (Text wie auf der Beitragen-Seite),
 * im selben Muster auch fuer Posts,
 * und ueber den Treffern ein zugeklappter Rat, dass nicht jede Aussage eine
 * Antwort braucht.
 */
describe('ResultViewComponent: Erklaerung der Beitragstypen und Rat zum Antworten', () => {
  const KOMMENTAR_SATZ = 'Eine Antwort, die du direkt posten kannst.';
  const HINTERGRUND_SATZ = 'Fakten und Zahlen, die eine Antwort stützen.';
  const POST_SATZ = 'Ein gelungener Beitrag aus einem sozialen Netzwerk, zum Teilen.';

  let fixture: ComponentFixture<ResultViewComponent>;

  function oeffnen(mobil: boolean, kommentare: number, hintergrund: number, posts = 0): HTMLElement {
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
      statement_text: 'waermepumpe teuer',
      commentary_search_results_count: kommentare,
      commentary_search_results: [],
      generictext_search_results_count: hintergrund,
      generictext_search_results: [],
      post_search_results_count: posts,
      post_search_results: [],
    });
    fixture = TestBed.createComponent(ResultViewComponent);
    fixture.detectChanges();
    return fixture.nativeElement;
  }

  function erklaerungen(seite: HTMLElement): string[] {
    return Array.from(seite.querySelectorAll('.typ-erklaerung')).map((e) => (e.textContent ?? '').trim());
  }

  /** Der Rat ist ein ruhiger, offener Hinweis unter den Treffern, kein Aufklapper (#602). */
  function pruefeRat(seite: HTMLElement): HTMLElement {
    const raete = seite.querySelectorAll<HTMLElement>('.keine-antwort-noetig');
    expect(raete.length).withContext('genau ein Rat').toBe(1);
    const rat = raete[0];
    expect(rat.querySelector('details, summary')).withContext('kein Aufklapper').toBeNull();
    expect(rat.classList).withContext('kein Hinweiskasten').not.toContain('hinweis-box');
    expect(rat.querySelector('mat-icon')).withContext('Info-Symbol').toBeTruthy();
    expect(rat.textContent).toContain('Nicht jede Aussage braucht eine Antwort');
    expect(rat.textContent).withContext('Melden auf der Plattform, nicht hier').toContain('auf der Plattform melden');
    return rat;
  }

  function steht(vorher: Element, nachher: Element): boolean {
    return (vorher.compareDocumentPosition(nachher) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
  }

  it('erklaert am Desktop beide Beitragstypen unter ihren Ueberschriften', () => {
    const seite = oeffnen(false, 2, 1);
    expect(erklaerungen(seite)).toEqual([KOMMENTAR_SATZ, HINTERGRUND_SATZ]);
    // Die Zeile steht direkt unter der Ueberschrift ihres Abschnitts.
    expect(seite.querySelector('app-commentary-search-results h2 + .typ-erklaerung')?.textContent).toContain(KOMMENTAR_SATZ);
    expect(seite.querySelector('app-generictext-search-results h2 + .typ-erklaerung')?.textContent).toContain(HINTERGRUND_SATZ);
  });

  it('erklaert am Desktop auch Posts unter ihrer Ueberschrift', () => {
    const seite = oeffnen(false, 2, 1, 1);
    expect(erklaerungen(seite)).toEqual([KOMMENTAR_SATZ, HINTERGRUND_SATZ, POST_SATZ]);
    expect(seite.querySelector('.post-ergebnisse h2 + .typ-erklaerung')?.textContent).toContain(POST_SATZ);
  });

  it('zeigt am Desktop unter den Treffern den ruhigen Rat', () => {
    const seite = oeffnen(false, 2, 0);
    const rat = pruefeRat(seite);
    // Auch der Abschnitt ohne Treffer erklaert seinen Typ.
    expect(erklaerungen(seite)).toEqual([KOMMENTAR_SATZ, HINTERGRUND_SATZ]);
    expect(steht(seite.querySelector('app-kartenliste')!, rat)).withContext('Rat steht nach den Treffern').toBeTrue();
    expect(steht(seite.querySelector('.nicht-dabei-unten')!, rat)).withContext('und nach "Nicht dabei?"').toBeTrue();
    expect(rat.closest('section')).withContext('kein eigener Abschnitt ohne Ueberschrift').toBeNull();
  });

  it('zeigt die Treffer am Desktop als Raster statt im Karussell', () => {
    const seite = oeffnen(false, 2, 1, 1);
    expect(seite.querySelector('app-result-carousel')).withContext('kein Karussell').toBeNull();
    const listen = seite.querySelectorAll('app-kartenliste ul.kartenliste--spalten');
    expect(listen.length).withContext('je Beitragstyp ein Raster').toBe(3);
  });

  it('erklaert am Handy den Beitragstyp des offenen Tabs', () => {
    const seite = oeffnen(true, 2, 1);
    expect(erklaerungen(seite)).toEqual([KOMMENTAR_SATZ]);

    fixture.componentInstance.switchToSection('generictext');
    fixture.debugElement.injector.get(ChangeDetectorRef).markForCheck();
    fixture.detectChanges();
    expect(erklaerungen(seite)).toEqual([HINTERGRUND_SATZ]);
  });

  it('erklaert am Handy auch Posts im Post-Tab', () => {
    const seite = oeffnen(true, 2, 1, 1);
    fixture.componentInstance.switchToSection('post');
    fixture.debugElement.injector.get(ChangeDetectorRef).markForCheck();
    fixture.detectChanges();
    expect(erklaerungen(seite)).toEqual([POST_SATZ]);
  });

  it('zeigt am Handy unter den Treffern den ruhigen Rat', () => {
    const seite = oeffnen(true, 0, 1);
    const rat = pruefeRat(seite);
    expect(steht(seite.querySelector('.mobile-section')!, rat)).withContext('Rat steht nach den Treffern').toBeTrue();
    expect(steht(seite.querySelector('.mobile-ergaenzen')!, rat)).withContext('und nach "Nicht dabei?"').toBeTrue();
  });

  for (const mobil of [false, true]) {
    it(`zeigt den Rat auch, wenn nur Posts treffen (${mobil ? 'Handy' : 'Desktop'})`, () => {
      pruefeRat(oeffnen(mobil, 0, 0, 1));
    });
  }

  for (const mobil of [false, true]) {
    it(`laesst die Seite ohne Treffer unveraendert (${mobil ? 'Handy' : 'Desktop'})`, () => {
      const seite = oeffnen(mobil, 0, 0);
      expect(seite.querySelector('.keine-antwort-noetig')).toBeNull();
      expect(erklaerungen(seite)).toEqual([]);
    });
  }
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

      expect(fixture.componentInstance.kommentarKarten.map((k) => k.id)).toEqual(['k-1']);
      expect(seite.textContent).toContain('Tempo 120 spart CO2');
      expect(seite.textContent).not.toContain('Tempolimit rettet Leben');

      filterKnoepfe(seite).find((k) => k.textContent?.trim() === 'Alle Themen')!.click();
      fixture.detectChanges();
      expect(fixture.componentInstance.kommentarKarten.map((k) => k.id)).toEqual(['k-1', 'k-2']);
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
    expect(fixture.componentInstance.kommentarKarten.map((k) => k.id)).toEqual(['k-9']);
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
    statementService = jasmine.createSpyObj('StatementService', ['aussageVorschlaege']);
    statementService.aussageVorschlaege.and.returnValue(of(vorschlaege));
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
    expect(statementService.aussageVorschlaege).toHaveBeenCalledWith('waermepumpe teuer');
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

  it('fuehrt ohne Treffer mit "Selbst beantworten" ins Kommentarformular, Aussage vorbelegt', fakeAsync(() => {
    const seite = oeffnen(true, false);
    const knopf = seite.querySelector<HTMLButtonElement>('.mobile-empty-state app-nicht-dabei .mobile-action-buttons button')!;
    expect(knopf.textContent).toContain('Selbst beantworten');

    knopf.click();
    tick();
    expect(router.url).toBe(`/workflow/add-commentary?aussage=${AUSSAGE_ID}`);
  }));

  it('zeigt am Desktop unter den Treffern "Nicht dabei?" ohne die Aussage der Treffer', fakeAsync(() => {
    const seite = oeffnen(false, true);
    const unten = seite.querySelector<HTMLElement>('.nicht-dabei-unten')!;

    expect(seite.querySelector('.unified-empty-state')).toBeNull();
    expect(unten.textContent).toContain('Nicht dabei?');
    expect(aehnliche(unten)).toEqual(['Wärmepumpen lohnen sich nicht']);

    unten.querySelector<HTMLButtonElement>('.neu-anlegen-knopf button')!.click();
    tick();
    expect(router.url).toBe(`/workflow/add-commentary?aussage=${AUSSAGE_ID}`);
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
      }),
    ).toEqual(['a', 'b', 'c']);
  });
});

/**
 * Die erkannte Aussage einmal ueber den Treffern (#642, R40): "Gefunden zu: ..." mit
 * "Nicht gemeint?"; die Karten zeigen ihren Antwort-auf-Kopf nur, wenn er abweicht.
 */
describe('ResultViewComponent: Gefunden zu', () => {
  const ERKANNT_ID = '22222222-2222-4333-8444-555555555555';
  const ANDERE_ID = '44444444-2222-4333-8444-555555555555';
  const ERKANNT = 'Ein Tempolimit bringt doch nichts fürs Klima!';
  const ANDERE = 'Tempolimit ist Bevormundung';

  let fixture: ComponentFixture<ResultViewComponent>;

  function kommentar(id: string, statementId: string | null, statementText: string, score: number): any {
    return {
      score,
      statement_id: statementId,
      statement_text: statementText,
      statement_similarity_score: 0.9,
      reply_relevance: 0.8,
      commentary_result: { id, content_type: 'commentary', title: `Kommentar ${id}`, text: 'Text', references: [] },
    };
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
      query_was_newly_added_as_statement: true,
      statement_id: '11111111-2222-4333-8444-555555555555',
      statement_text: 'tempolimit bringt nichts',
      commentary_search_results_count: kommentare.length,
      commentary_search_results: kommentare,
      generictext_search_results_count: 0,
      generictext_search_results: [],
    });
    fixture = TestBed.createComponent(ResultViewComponent);
    fixture.detectChanges();
    fixture.componentInstance.searchQuery = 'tempolimit bringt nichts';
    fixture.debugElement.injector.get(ChangeDetectorRef).markForCheck();
    fixture.detectChanges();
    return fixture.nativeElement;
  }

  const TREFFER = () => [
    kommentar('k-1', ERKANNT_ID, ERKANNT, 0.9),
    kommentar('k-2', ANDERE_ID, ANDERE, 0.85),
    kommentar('k-3', ERKANNT_ID, ERKANNT, 0.8),
    kommentar('k-4', null, '', 0.5),
  ];

  for (const mobil of [false, true]) {
    const wo = mobil ? 'Handy' : 'Desktop';

    it(`zeigt die erkannte Aussage einmal ueber den Treffern (${wo})`, () => {
      const seite = oeffnen(mobil, TREFFER());
      const bloecke = seite.querySelectorAll('.gefunden-zu');
      expect(bloecke.length).withContext('genau ein Block').toBe(1);
      expect(bloecke[0].querySelector('.gefunden-zu-satz')?.textContent?.replace(/\s+/g, ' ').trim())
        .toBe(`Gefunden zu: „${ERKANNT}“`);
      const nichtGemeint = seite.querySelectorAll('button.nicht-gemeint');
      expect(nichtGemeint.length).toBe(1);
      expect(nichtGemeint[0].textContent?.trim()).toBe('Nicht gemeint?');
      // Der Block steht vor der ersten Karte.
      const ersteKarte = seite.querySelector('app-kartenliste')!;
      expect(bloecke[0].compareDocumentPosition(ersteKarte) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    });

    it(`zeigt den Antwort-auf-Kopf nur an Karten mit abweichender Aussage (${wo})`, () => {
      const seite = oeffnen(mobil, TREFFER());
      const vorschauen = Array.from(seite.querySelectorAll('.statement-vorschau')).map((e) => e.textContent!.trim());
      expect(vorschauen).toEqual([`„${ANDERE}“`]);
      const karten = fixture.componentInstance.kommentarKarten;
      expect(karten.map((k) => k.statement?.text ?? null)).toEqual([null, ANDERE, null, null]);
    });

    it(`fuehrt mit "Nicht gemeint?" zu "Nicht dabei?" unter den Treffern (${wo})`, () => {
      const seite = oeffnen(mobil, TREFFER());
      const ziel = seite.querySelector<HTMLElement>('#nicht-dabei-unten')!;
      expect(ziel).withContext('Anker unter den Treffern').toBeTruthy();
      expect(ziel.querySelector('app-nicht-dabei')).toBeTruthy();
      const scroll = spyOn(ziel, 'scrollIntoView');

      seite.querySelector<HTMLButtonElement>('button.nicht-gemeint')!.click();

      expect(scroll).toHaveBeenCalled();
      expect(document.activeElement).toBe(ziel);
    });
  }

  it('zeigt keinen Block, wenn kein Treffer ueber eine Aussage kam', () => {
    const seite = oeffnen(false, [kommentar('k-4', null, '', 0.5)]);
    expect(seite.querySelector('.gefunden-zu')).toBeNull();
  });

  it('sagt unter den Treffern "zu dieser Aussage", nicht "zu deiner Aussage" (R49)', () => {
    const seite = oeffnen(false, TREFFER());
    expect(seite.querySelector('.nicht-dabei-unten .neu-anlegen-satz')?.textContent?.trim())
      .toBe('Schreib selbst eine Antwort zu dieser Aussage.');
    expect(seite.textContent).not.toContain('zu deiner Aussage');
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

  for (const [mobil, bereich] of [[false, '.unified-empty-state'], [true, '.mobile-empty-state']] as const) {
    it(`bietet "Oft gesucht" und sagt "zu dieser Aussage" (${mobil ? 'Handy' : 'Desktop'})`, () => {
      const seite = oeffnen(mobil);
      const leer = seite.querySelector(bereich)!;
      expect(leer.querySelector('app-oft-gesucht')).withContext('Anschluss statt Sackgasse').toBeTruthy();
      expect(leer.querySelector('.hier-fehlt-link')?.getAttribute('href')).toBe('/hier-fehlt-eine-antwort');
      expect(leer.querySelector('.neu-anlegen-satz')?.textContent?.trim()).toBe('Schreib die erste Antwort zu dieser Aussage.');
      expect(seite.querySelector('.gefunden-zu')).toBeNull();
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

  it('gibt null, wenn nur direkte Treffer ohne Aussage da sind', () => {
    expect(erkannteAussage(antwort([treffer(null, '', 0.9)]))).toBeNull();
  });
});
