import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { routes } from '../app.routes';
import { ohneWaechter } from '../testing/routen-ohne-waechter';
import { SearchResponse } from '../services/dtos/searchDtos';

import { CommentarySearchResultsComponent } from './commentary-search-results.component';

describe('CommentarySearchResultsComponent', () => {
  let component: CommentarySearchResultsComponent;
  let fixture: ComponentFixture<CommentarySearchResultsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CommentarySearchResultsComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(CommentarySearchResultsComponent);
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
describe('CommentarySearchResultsComponent: Klick auf Hinzufuegen', () => {
  let fixture: ComponentFixture<CommentarySearchResultsComponent>;
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
      imports: [CommentarySearchResultsComponent],
      providers: [provideRouter(ohneWaechter(routes)), provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    router = TestBed.inject(Router);
    fixture = TestBed.createComponent(CommentarySearchResultsComponent);
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

    expect(router.url).toBe(`/workflow/add-commentary?aussage=${AUSSAGE_ID}`);
  }));

  it('faellt ohne gueltige ID auf den Text der Aussage zurueck', fakeAsync(() => {
    // Das Backend schreibt eine gescheiterte Anlage als "None" in die Antwort.
    fixture.componentRef.setInput('searchResponse', antwort('None'));

    klicken();

    expect(router.url).toBe('/workflow/add-commentary?searchQuery=Waermepumpen%20sind%20zu%20teuer');
  }));
});
