import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { routes } from '../app.routes';
import { ohneWaechter } from '../testing/routen-ohne-waechter';
import { SearchResponse } from '../services/dtos/searchDtos';

import { GenerictextSearchResultsComponent } from './generictext-search-results.component';

describe('GenerictextSearchResultsComponent', () => {
  let component: GenerictextSearchResultsComponent;
  let fixture: ComponentFixture<GenerictextSearchResultsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [GenerictextSearchResultsComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(GenerictextSearchResultsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

/**
 * Echter Klick auf den Knopf, echte Routentabelle: Wo landet man wirklich?
 * Ziel ist die Formularseite mit der ID der Aussage, nicht mehr /contribute.
 */
describe('GenerictextSearchResultsComponent: Klick auf Hinzufuegen', () => {
  let fixture: ComponentFixture<GenerictextSearchResultsComponent>;
  let router: Router;

  const AUSSAGE_ID = '11111111-2222-4333-8444-555555555555';

  function antwort(statementId: string): SearchResponse {
    return {
      query_was_newly_added_as_statement: false,
      statement_id: statementId,
      statement_text: 'Waermepumpen sind zu teuer',
      commentary_search_results_count: 0,
      commentary_search_results: [],
      generictext_search_results_count: 0,
      generictext_search_results: [],
    };
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [GenerictextSearchResultsComponent],
      providers: [provideRouter(ohneWaechter(routes)), provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    router = TestBed.inject(Router);
    fixture = TestBed.createComponent(GenerictextSearchResultsComponent);
    fixture.componentRef.setInput('searchQuery', 'waermepumpe teuer');
  });

  function klicken(): void {
    fixture.detectChanges();
    const knopf: HTMLButtonElement = fixture.nativeElement.querySelector('button.gutgesagt-primary-dark');
    expect(knopf).withContext('Hinzufuegen-Knopf im leeren Zustand').toBeTruthy();
    knopf.click();
    tick();
  }

  it('fuehrt ins Formular mit der Aussage-ID', fakeAsync(() => {
    fixture.componentRef.setInput('searchResponse', antwort(AUSSAGE_ID));

    klicken();

    expect(router.url).toBe(`/workflow/add-generictext?aussage=${AUSSAGE_ID}`);
  }));

  it('faellt ohne gueltige ID auf den Text der Aussage zurueck', fakeAsync(() => {
    // Das Backend schreibt eine gescheiterte Anlage als "None" in die Antwort.
    fixture.componentRef.setInput('searchResponse', antwort('None'));

    klicken();

    expect(router.url).toBe('/workflow/add-generictext?searchQuery=Waermepumpen%20sind%20zu%20teuer');
  }));
});

/**
 * Abschnitt Hintergrundinfos (#642, R66): Singular und Plural, und dieselbe Form wie
 * bei den Kommentaren - ein schlichter Link, kein voller Knopf.
 */
describe('GenerictextSearchResultsComponent: Zaehler und Link', () => {
  let fixture: ComponentFixture<GenerictextSearchResultsComponent>;

  function antwort(anzahl: number): SearchResponse {
    return {
      query_was_newly_added_as_statement: false,
      statement_id: '11111111-2222-4333-8444-555555555555',
      statement_text: 'Atomkraft ist günstig',
      commentary_search_results_count: 1,
      commentary_search_results: [],
      generictext_search_results_count: anzahl,
      generictext_search_results: [],
    };
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [GenerictextSearchResultsComponent],
      providers: [provideRouter(ohneWaechter(routes)), provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    fixture = TestBed.createComponent(GenerictextSearchResultsComponent);
  });

  function zeigen(anzahl: number, minimal = false): HTMLElement {
    fixture.componentRef.setInput('searchResponse', antwort(anzahl));
    fixture.componentRef.setInput('showMinimalEmptyState', minimal);
    fixture.detectChanges();
    return fixture.nativeElement;
  }

  const zaehler = (seite: HTMLElement) => (seite.querySelector('.result-count')?.textContent ?? '').replace(/\s+/g, ' ').trim();

  it('sagt bei einem Treffer "1 passende Hintergrundinfo"', () => {
    expect(zaehler(zeigen(1))).toBe('1 passende Hintergrundinfo gefunden.');
  });

  it('sagt bei mehreren Treffern "passende Hintergrundinfos"', () => {
    expect(zaehler(zeigen(3))).toBe('3 passende Hintergrundinfos gefunden.');
  });

  for (const [fall, anzahl, minimal] of [['mit Treffern', 2, false], ['ohne Hintergrundinfos, mit anderen Treffern', 0, true]] as const) {
    it(`bietet ${fall} das Ergaenzen als schlichten Link an, ohne "Hilf der Community"`, () => {
      const seite = zeigen(anzahl, minimal);
      const knoepfe: HTMLButtonElement[] = Array.from(seite.querySelectorAll('button'));
      expect(knoepfe.map((k) => k.textContent!.trim())).toEqual(['Hintergrundinfo ergänzen']);
      expect(knoepfe[0].classList).toContain('ergaenzen-link');
      expect(knoepfe[0].hasAttribute('mat-raised-button')).toBeFalse();
      expect(seite.textContent).not.toContain('Hilf der Community');
    });
  }
});
