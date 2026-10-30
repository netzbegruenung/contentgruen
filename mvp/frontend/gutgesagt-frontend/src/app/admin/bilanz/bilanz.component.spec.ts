import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { BilanzComponent } from './bilanz.component';
import { BilanzResponse } from '../../services/dtos/metricsDtos';
import { environment } from '../../../environments/environment';

const URL = `${environment.baseUrl}/api/v1/metrics/bilanz?wochen=8`;

const ANTWORT: BilanzResponse = {
  wochen: 8,
  woechentlich: [
    {
      woche_ab: '2026-10-26',
      tage: 4,
      suchen: 40,
      personen_pro_tag: 2.5,
      nutzungen: 12,
      anteil_ohne_treffer: 37.5,
      nutzungen_je_suche: 0.3,
    },
    {
      woche_ab: '2026-10-19',
      tage: 7,
      suchen: 0,
      personen_pro_tag: 0,
      nutzungen: null,
      anteil_ohne_treffer: null,
      nutzungen_je_suche: null,
    },
  ],
};

describe('BilanzComponent', () => {
  let fixture: ComponentFixture<BilanzComponent>;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [BilanzComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(BilanzComponent);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  });

  afterEach(() => http.verify());

  function element(): HTMLElement {
    return fixture.nativeElement as HTMLElement;
  }

  function zeilen(): string[][] {
    return Array.from(element().querySelectorAll('[data-testid="bilanz-woche"]')).map((z) =>
      Array.from(z.querySelectorAll('th, td')).map((zelle) => zelle.textContent?.trim().replace(/\s+/g, ' ') ?? '')
    );
  }

  it('zeigt K1, K2, K3 und H je Woche, die laufende zuerst', () => {
    http.expectOne(URL).flush(ANTWORT);
    fixture.detectChanges();

    expect(zeilen()).toEqual([
      ['ab 26.10.2026 (laufend, 4 Tage)', '2,5', '12', '37,5 %', '0,3', '40'],
      ['ab 19.10.2026', '0', '–', '–', '–', '0'],
    ]);
    const kopf = element().querySelector('thead')?.textContent ?? '';
    expect(kopf).toContain('Personen pro Tag, die suchen');
    expect(kopf).toContain('Nutzungen');
    expect(kopf).toContain('Suchen ohne Treffer');
    expect(kopf).toContain('Nutzungen je Suche');
  });

  it('zeigt keine Zielwerte', () => {
    http.expectOne(URL).flush(ANTWORT);
    fixture.detectChanges();

    // Der Untertitel sagt ausdruecklich, dass es keine Ziele gibt.
    expect(element().textContent).toContain('Feste Ziele gibt es nicht');
    expect(element().textContent).not.toMatch(/Ziel erreicht|Zielwert|\/ \d/);
  });

  it('erklärt, warum ein Wert fehlt', () => {
    http.expectOne(URL).flush(ANTWORT);
    fixture.detectChanges();

    expect(element().textContent).toContain('– heißt: nicht bekannt');
  });

  it('lädt einen längeren Zeitraum, damit die Basislinie sichtbar bleibt', () => {
    http.expectOne(URL).flush(ANTWORT);
    fixture.detectChanges();

    const auswahl = element().querySelector('select') as HTMLSelectElement;
    expect(Array.from(auswahl.options).map((o) => o.value)).toEqual(['8', '13', '26', '52']);
    auswahl.value = '52';
    auswahl.dispatchEvent(new Event('change'));
    fixture.detectChanges();

    http.expectOne(`${environment.baseUrl}/api/v1/metrics/bilanz?wochen=52`).flush({ ...ANTWORT, wochen: 52 });
    fixture.detectChanges();
    expect(element().textContent).toContain('die letzten 52');
  });

  it('verwirft die Antwort eines vorher gewählten Zeitraums', () => {
    http.expectOne(URL).flush(ANTWORT);
    fixture.detectChanges();

    const auswahl = element().querySelector('select') as HTMLSelectElement;
    auswahl.value = '52';
    auswahl.dispatchEvent(new Event('change'));
    const alt = http.expectOne(`${environment.baseUrl}/api/v1/metrics/bilanz?wochen=52`);
    auswahl.value = '13';
    auswahl.dispatchEvent(new Event('change'));

    expect(alt.cancelled).toBeTrue();
    http.expectOne(`${environment.baseUrl}/api/v1/metrics/bilanz?wochen=13`).flush({ ...ANTWORT, wochen: 13 });
    fixture.detectChanges();
    expect(element().textContent).toContain('die letzten 13');
  });

  it('zeigt nach einem Ladefehler keine Tabelle eines anderen Zeitraums', () => {
    http.expectOne(URL).flush(ANTWORT);
    fixture.detectChanges();

    const auswahl = element().querySelector('select') as HTMLSelectElement;
    auswahl.value = '52';
    auswahl.dispatchEvent(new Event('change'));
    http
      .expectOne(`${environment.baseUrl}/api/v1/metrics/bilanz?wochen=52`)
      .flush('kaputt', { status: 500, statusText: 'Server Error' });
    fixture.detectChanges();

    expect(element().textContent).toContain('konnte nicht geladen werden');
    expect(zeilen()).toEqual([]);
  });

  it('nennt die laufende Woche vorläufig', () => {
    http.expectOne(URL).flush(ANTWORT);
    fixture.detectChanges();

    expect(element().textContent).toContain('Die laufende Woche ist vorläufig');
  });

  it('meldet einen Ladefehler', () => {
    http.expectOne(URL).flush('kaputt', { status: 500, statusText: 'Server Error' });
    fixture.detectChanges();

    expect(element().textContent).toContain('konnte nicht geladen werden');
  });
});
