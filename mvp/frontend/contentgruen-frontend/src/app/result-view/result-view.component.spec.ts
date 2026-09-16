import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { BreakpointObserver } from '@angular/cdk/layout';
import { of } from 'rxjs';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
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

  for (const fehlend of [null, '', 'None']) {
    it(`nimmt bei fehlender ID (${JSON.stringify(fehlend)}) den Suchtext`, fakeAsync(() => {
      oeffnen(false, fehlend);

      knopf('.action-buttons-top', 0).click();
      tick();
      expect(router.url).toBe('/workflow/add-commentary?searchQuery=waermepumpe%20teuer');
    }));
  }

  it('vergisst die Aussage der vorigen Suche, sobald eine neue laeuft', fakeAsync(() => {
    oeffnen(false, AUSSAGE_ID);
    const zustand = TestBed.inject(StateManagementService);
    zustand.setStatementId('22222222-2222-4333-8444-555555555555');

    // Neue Suche startet: statementId wird sofort geleert, die alte Antwort
    // steht noch im Zustand, zaehlt aber waehrend des Ladens nicht.
    const komponente = fixture.componentInstance as unknown as { performSearchWithStatement(): void };
    komponente.performSearchWithStatement();
    zustand.setLoading(true);

    expect(zustand.currentState.statementId).toBeNull();
    fixture.componentInstance.navigateToContribute('commentary');
    tick();
    expect(router.url).toBe('/workflow/add-commentary?searchQuery=waermepumpe%20teuer');
  }));
});
