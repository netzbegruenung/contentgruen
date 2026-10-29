import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { TESTSET_DATEI, ThemenZuordnenComponent } from './themen-zuordnen.component';
import { environment } from '../../../environments/environment';

const THEMEN_URL = `${environment.baseUrl}/api/v1/statement/themen`;
const THEMEN = [
  { schluessel: 'klima', name: 'Klima' },
  { schluessel: 'verkehr', name: 'Verkehr' },
];

describe('ThemenZuordnenComponent', () => {
  let fixture: ComponentFixture<ThemenZuordnenComponent>;
  let http: HttpTestingController;

  function element(): HTMLElement {
    return fixture.nativeElement as HTMLElement;
  }

  function zeilen(): HTMLElement[] {
    return Array.from(element().querySelectorAll('[data-testid="aussage-zum-zuordnen"]'));
  }

  function knopf(bereich: Element, name: string): HTMLButtonElement {
    const knoepfe = Array.from(bereich.querySelectorAll('button')) as HTMLButtonElement[];
    return knoepfe.find((k) => k.textContent?.trim() === name)!;
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ThemenZuordnenComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideNoopAnimations()],
    }).compileComponents();
    fixture = TestBed.createComponent(ThemenZuordnenComponent);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
    http.expectOne(THEMEN_URL).flush({ themen: THEMEN });
    http.expectOne(`${THEMEN_URL}/aussagen`).flush({
      aussagen: [
        { statement_id: 'a-1', statement_text: 'Windräder töten Vögel', themen: [] },
        { statement_id: 'a-2', statement_text: 'Tempolimit bringt nichts', themen: [THEMEN[1]] },
      ],
    });
    fixture.detectChanges();
  });

  afterEach(() => http.verify());

  it('zeigt alle Aussagen mit ihren Themen und den Stand', () => {
    expect(zeilen().length).toBe(2);
    expect(knopf(zeilen()[1], 'Verkehr').getAttribute('aria-pressed')).toBe('true');
    expect(element().textContent).toContain('1 von 2 Aussagen haben ein Thema');
  });

  it('speichert eine Zuordnung sofort', () => {
    knopf(zeilen()[0], 'Klima').click();

    const anfrage = http.expectOne(`${THEMEN_URL}/zuordnen`);
    expect(anfrage.request.method).toBe('PUT');
    expect(anfrage.request.body).toEqual({ statement_id: 'a-1', themen: ['klima'] });
    anfrage.flush({ statement_id: 'a-1', themen: [THEMEN[0]] });
    fixture.detectChanges();

    expect(element().textContent).toContain('2 von 2 Aussagen haben ein Thema');
  });

  it('lädt das Testset als JSON-Datei herunter', () => {
    const link = document.createElement('a');
    spyOn(link, 'click');
    spyOn(document, 'createElement').and.returnValue(link);

    knopf(element(), 'download Testset herunterladen').click();
    http.expectOne(`${THEMEN_URL}/testset`).flush({
      zuordnungen: [{ statement_id: 'a-2', text: 'Tempolimit bringt nichts', themen: ['verkehr'], quelle: 'von_hand' }],
    });

    expect(link.download).toBe(TESTSET_DATEI);
    expect(link.click).toHaveBeenCalled();
  });
});
