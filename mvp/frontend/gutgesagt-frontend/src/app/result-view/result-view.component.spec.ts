import { ChangeDetectorRef } from '@angular/core';
import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { BreakpointObserver } from '@angular/cdk/layout';
import { of } from 'rxjs';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter, Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';

import { ResultViewComponent } from './result-view.component';
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
    expect(oben.textContent).toContain('Eigenen Kommentar ergänzen');
    expect(unten.textContent).toContain('Kommentar ergänzen');
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
 * Nutzertest: Was ein Kommentar und was eine Hintergrundinfo ist, war auf der
 * Ergebnisseite nicht klar. Je eine Erklaerzeile (Text wie auf der Beitragen-Seite)
 * und ueber den Treffern ein zugeklappter Rat, dass nicht jede Aussage eine
 * Antwort braucht.
 */
describe('ResultViewComponent: Erklaerung der Beitragstypen und Rat zum Antworten', () => {
  const KOMMENTAR_SATZ = 'Eine Antwort, die du direkt posten kannst.';
  const HINTERGRUND_SATZ = 'Fakten und Zahlen, die eine Antwort stützen.';

  let fixture: ComponentFixture<ResultViewComponent>;

  function oeffnen(mobil: boolean, kommentare: number, hintergrund: number): HTMLElement {
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
    });
    fixture = TestBed.createComponent(ResultViewComponent);
    fixture.detectChanges();
    return fixture.nativeElement;
  }

  function erklaerungen(seite: HTMLElement): string[] {
    return Array.from(seite.querySelectorAll('.typ-erklaerung')).map((e) => (e.textContent ?? '').trim());
  }

  function pruefeRat(seite: HTMLElement): void {
    const raete = seite.querySelectorAll<HTMLDetailsElement>('details.keine-antwort-noetig');
    expect(raete.length).withContext('genau ein Rat').toBe(1);
    const rat = raete[0];
    expect(rat.open).withContext('standardmaessig zugeklappt').toBeFalse();
    expect(rat.querySelector('summary')?.textContent).toContain('Nicht jede Aussage braucht eine Antwort');
    expect(rat.textContent).toContain('melden');

    rat.querySelector('summary')!.click();
    expect(rat.open).withContext('laesst sich aufklappen').toBeTrue();
  }

  it('erklaert am Desktop beide Beitragstypen unter ihren Ueberschriften', () => {
    const seite = oeffnen(false, 2, 1);
    expect(erklaerungen(seite)).toEqual([KOMMENTAR_SATZ, HINTERGRUND_SATZ]);
    // Die Zeile steht direkt unter der Ueberschrift ihres Abschnitts.
    expect(seite.querySelector('app-commentary-search-results h2 + .typ-erklaerung')?.textContent).toContain(KOMMENTAR_SATZ);
    expect(seite.querySelector('app-generictext-search-results h2 + .typ-erklaerung')?.textContent).toContain(HINTERGRUND_SATZ);
  });

  it('zeigt am Desktop ueber den Treffern den zugeklappten Rat', () => {
    const seite = oeffnen(false, 2, 0);
    pruefeRat(seite);
    const rat = seite.querySelector('details.keine-antwort-noetig')!;
    const ersterAbschnitt = seite.querySelector('app-commentary-search-results')!;
    expect(rat.compareDocumentPosition(ersterAbschnitt) & Node.DOCUMENT_POSITION_FOLLOWING)
      .withContext('Rat steht vor den Treffern').toBeTruthy();
  });

  it('erklaert am Handy den Beitragstyp des offenen Tabs', () => {
    const seite = oeffnen(true, 2, 1);
    expect(erklaerungen(seite)).toEqual([KOMMENTAR_SATZ]);

    fixture.componentInstance.switchToSection('generictext');
    fixture.debugElement.injector.get(ChangeDetectorRef).markForCheck();
    fixture.detectChanges();
    expect(erklaerungen(seite)).toEqual([HINTERGRUND_SATZ]);
  });

  it('zeigt am Handy ueber den Tabs den zugeklappten Rat', () => {
    const seite = oeffnen(true, 0, 1);
    pruefeRat(seite);
    const rat = seite.querySelector('details.keine-antwort-noetig')!;
    expect(rat.compareDocumentPosition(seite.querySelector('.mobile-tab-bar')!) & Node.DOCUMENT_POSITION_FOLLOWING)
      .withContext('Rat steht vor den Tabs').toBeTruthy();
  });

  for (const mobil of [false, true]) {
    it(`laesst die Seite ohne Treffer unveraendert (${mobil ? 'Handy' : 'Desktop'})`, () => {
      const seite = oeffnen(mobil, 0, 0);
      expect(seite.querySelector('details.keine-antwort-noetig')).toBeNull();
      expect(erklaerungen(seite)).toEqual([]);
    });
  }
});
