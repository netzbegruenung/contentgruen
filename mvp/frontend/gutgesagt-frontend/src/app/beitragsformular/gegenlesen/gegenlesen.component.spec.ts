import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { GegenlesenComponent } from './gegenlesen.component';
import { GEGENLESEN_VERZOEGERUNG_MS, Gegengelesen } from './gegenlesen.service';
import { environment } from '../../../environments/environment';

const PFAD = `${environment.baseUrl}/api/v1/gegenlesen`;

const MIT_ANMERKUNG: Gegengelesen = {
  guete: 7,
  anmerkungen: [
    {
      art: 'verneinung',
      stelle: 'titel',
      text: 'Der Titel beginnt mit „Nicht“. Sag lieber, was stimmt.',
      woerter: ['Nicht'],
    },
  ],
};

/**
 * Gegenlesen beim Schreiben (#358): etwa eine Sekunde nach der letzten Eingabe fragt das
 * Formular den Dienst, zeigt das Siegel mit dem Kriterienanteil der Güte und darunter die
 * Anmerkungen. Nur die schreibende Person sieht das; Speichern sperrt es nie.
 */
describe('GegenlesenComponent', () => {
  let fixture: ComponentFixture<GegenlesenComponent>;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [GegenlesenComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    fixture = TestBed.createComponent(GegenlesenComponent);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  });

  afterEach(() => http.verify());

  function schreibe(titel: string, text = '', aussage = ''): void {
    fixture.componentRef.setInput('titel', titel);
    fixture.componentRef.setInput('text', text);
    fixture.componentRef.setInput('aussage', aussage);
    fixture.detectChanges();
  }

  const element = (): HTMLElement => fixture.nativeElement as HTMLElement;
  const siegelText = (): string | null => element().querySelector('app-siegel svg')?.getAttribute('aria-label') ?? null;

  it('fragt erst eine Sekunde nach der letzten Eingabe, einmal', fakeAsync(() => {
    schreibe('Nicht die');
    tick(GEGENLESEN_VERZOEGERUNG_MS - 100);
    schreibe('Nicht die Wärmepumpe ist das Problem', '', 'Wärmepumpen sind zu teuer');
    tick(GEGENLESEN_VERZOEGERUNG_MS - 1);
    http.expectNone(PFAD);

    tick(1);
    const anfrage = http.expectOne(PFAD);
    expect(anfrage.request.method).toBe('POST');
    expect(anfrage.request.body).toEqual({
      titel: 'Nicht die Wärmepumpe ist das Problem',
      text: '',
      aussage: 'Wärmepumpen sind zu teuer',
    });
    anfrage.flush(MIT_ANMERKUNG);
  }));

  it('zeigt das Siegel mit der Güte und die Anmerkungen darunter', fakeAsync(() => {
    schreibe('Nicht die Wärmepumpe ist das Problem');
    tick(GEGENLESEN_VERZOEGERUNG_MS);
    http.expectOne(PFAD).flush(MIT_ANMERKUNG);
    fixture.detectChanges();

    expect(siegelText()).toBe('Siegel: Güte 7 von 10');
    const anmerkungen = Array.from(element().querySelectorAll('.gegenlesen-anmerkung')).map((li) => li.textContent?.trim());
    expect(anmerkungen).toEqual(['Der Titel beginnt mit „Nicht“. Sag lieber, was stimmt.']);
    expect(element().textContent).toContain('Nur du siehst');
  }));

  it('sagt, wenn nichts aufgefallen ist', fakeAsync(() => {
    schreibe('Wärmepumpe lohnt sich auch im Altbau');
    tick(GEGENLESEN_VERZOEGERUNG_MS);
    http.expectOne(PFAD).flush({ guete: 10, anmerkungen: [] });
    fixture.detectChanges();

    expect(siegelText()).toBe('Siegel: Güte 10 von 10');
    expect(element().querySelectorAll('.gegenlesen-anmerkung').length).toBe(0);
    expect(element().textContent).toContain('Nichts aufgefallen');
  }));

  it('dreht das Siegel nach oben, wenn der Text besser wird', fakeAsync(() => {
    schreibe('Nicht die Wärmepumpe ist das Problem');
    tick(GEGENLESEN_VERZOEGERUNG_MS);
    http.expectOne(PFAD).flush(MIT_ANMERKUNG);
    fixture.detectChanges();

    schreibe('Die Wärmepumpe löst das Problem');
    tick(GEGENLESEN_VERZOEGERUNG_MS);
    http.expectOne(PFAD).flush({ guete: 10, anmerkungen: [] });
    fixture.detectChanges();

    expect(siegelText()).toBe('Siegel: Güte 10 von 10');
    // Die Funken des Aufstiegs liefert app-siegel (#416); hier nur, dass sie ausgelöst werden.
    expect(element().querySelector('app-siegel')!.classList).toContain('springt');
    tick(1000);
  }));

  it('fragt ohne Titel und Text nicht und zeigt das Siegel als neu', fakeAsync(() => {
    schreibe('  ', '');
    tick(GEGENLESEN_VERZOEGERUNG_MS);
    http.expectNone(PFAD);

    expect(siegelText()).toBe('Siegel: neu, noch keine Güte');
    expect(element().querySelectorAll('.gegenlesen-anmerkung').length).toBe(0);
  }));

  it('verschwindet still, wenn der Dienst nicht antwortet', fakeAsync(() => {
    schreibe('Ein Titel');
    tick(GEGENLESEN_VERZOEGERUNG_MS);
    http.expectOne(PFAD).flush('weg', { status: 503, statusText: 'Service Unavailable' });
    fixture.detectChanges();

    expect(element().querySelector('.gegenlesen')).toBeNull();

    // Beim nächsten Schreiben versucht es es wieder.
    schreibe('Ein anderer Titel');
    tick(GEGENLESEN_VERZOEGERUNG_MS);
    http.expectOne(PFAD).flush(MIT_ANMERKUNG);
    fixture.detectChanges();
    expect(element().querySelector('.gegenlesen')).not.toBeNull();
  }));

  it('lässt beim Rate-Limit das letzte Ergebnis stehen', fakeAsync(() => {
    schreibe('Nicht die Wärmepumpe ist das Problem');
    tick(GEGENLESEN_VERZOEGERUNG_MS);
    http.expectOne(PFAD).flush(MIT_ANMERKUNG);
    fixture.detectChanges();

    schreibe('Nicht die Wärmepumpe ist das Problem, sagt sie');
    tick(GEGENLESEN_VERZOEGERUNG_MS);
    http.expectOne(PFAD).flush('zu viele', { status: 429, statusText: 'Too Many Requests' });
    fixture.detectChanges();

    expect(siegelText()).toBe('Siegel: Güte 7 von 10');
    expect(element().querySelectorAll('.gegenlesen-anmerkung').length).toBe(1);
  }));

  it('sagt neue Anmerkungen in einer Region an, die schon vorher da ist', fakeAsync(() => {
    const region = element().querySelector('[aria-live="polite"]');
    expect(region).not.toBeNull();

    schreibe('Nicht die Wärmepumpe ist das Problem');
    tick(GEGENLESEN_VERZOEGERUNG_MS);
    http.expectOne(PFAD).flush(MIT_ANMERKUNG);
    fixture.detectChanges();

    expect(element().querySelector('[aria-live="polite"]')).toBe(region);
    expect(region!.querySelector('.gegenlesen-anmerkung')).not.toBeNull();
  }));
});
