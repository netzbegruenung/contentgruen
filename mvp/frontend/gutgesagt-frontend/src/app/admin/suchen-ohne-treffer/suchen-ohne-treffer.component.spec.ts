import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { SuchenOhneTrefferComponent } from './suchen-ohne-treffer.component';
import { environment } from '../../../environments/environment';

const URL = `${environment.baseUrl}/api/v1/metrics/suchen-ohne-treffer`;

describe('SuchenOhneTrefferComponent', () => {
  let fixture: ComponentFixture<SuchenOhneTrefferComponent>;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SuchenOhneTrefferComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(SuchenOhneTrefferComponent);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  });

  afterEach(() => http.verify());

  function text(): string {
    return (fixture.nativeElement as HTMLElement).textContent ?? '';
  }

  it('zeigt die Aussagen mit Anzahl, absteigend wie geliefert', () => {
    http.expectOne(URL).flush({
      wochen: 4,
      mindestanzahl: 2,
      suchanfragen: [
        { text: 'Windräder töten Vögel', anzahl: 7 },
        { text: 'Wärmepumpe im Altbau', anzahl: 3 },
      ],
    });
    fixture.detectChanges();

    const zeilen = Array.from(
      (fixture.nativeElement as HTMLElement).querySelectorAll('[data-testid="suche-ohne-treffer"]')
    ).map((z) => Array.from(z.querySelectorAll('td')).map((td) => td.textContent?.trim()));

    expect(zeilen).toEqual([
      ['Windräder töten Vögel', '7'],
      ['Wärmepumpe im Altbau', '3'],
    ]);
    expect(text()).toContain('letzten 4 Wochen');
    expect(text()).toContain('Aussage');
  });

  it('nennt die Mindestanzahl als Personen, nicht als Suchen', () => {
    http.expectOne(URL).flush({ wochen: 4, mindestanzahl: 2, suchanfragen: [] });
    fixture.detectChanges();

    expect(text()).toContain('2 verschiedene Personen');
    expect(text()).not.toContain('ab 2 Suchen');
  });

  it('sagt, wenn es keine Suchanfrage ohne Treffer gibt', () => {
    http.expectOne(URL).flush({ wochen: 4, mindestanzahl: 2, suchanfragen: [] });
    fixture.detectChanges();

    expect(text()).toContain('Keine Suchanfrage ohne Treffer');
  });

  it('meldet einen Ladefehler', () => {
    http.expectOne(URL).flush('kaputt', { status: 500, statusText: 'Server Error' });
    fixture.detectChanges();

    expect(text()).toContain('konnten nicht geladen werden');
  });
});
