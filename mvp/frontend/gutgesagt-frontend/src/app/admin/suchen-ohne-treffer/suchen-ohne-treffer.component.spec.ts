import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { SuchenOhneTrefferComponent } from './suchen-ohne-treffer.component';
import { environment } from '../../../environments/environment';

const URL = `${environment.baseUrl}/api/v1/metrics/suchen-ohne-treffer`;

describe('SuchenOhneTrefferComponent', () => {
  let fixture: ComponentFixture<SuchenOhneTrefferComponent>;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SuchenOhneTrefferComponent, HttpClientTestingModule],
    }).compileComponents();

    fixture = TestBed.createComponent(SuchenOhneTrefferComponent);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  });

  afterEach(() => http.verify());

  function text(): string {
    return (fixture.nativeElement as HTMLElement).textContent ?? '';
  }

  it('zeigt die Suchanfragen mit Anzahl, absteigend wie geliefert', () => {
    http.expectOne(`${URL}?wochen=4`).flush({
      wochen: 4,
      mindestanzahl: 2,
      suchanfragen: [
        { statement_id: 'a', text: 'Windräder töten Vögel', anzahl: 7 },
        { statement_id: 'b', text: 'Wärmepumpe im Altbau', anzahl: 3 },
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
  });

  it('sagt, wenn es keine Suchanfrage ohne Treffer gibt', () => {
    http.expectOne(`${URL}?wochen=4`).flush({ wochen: 4, mindestanzahl: 2, suchanfragen: [] });
    fixture.detectChanges();

    expect(text()).toContain('Keine Suchanfrage ohne Treffer');
  });

  it('meldet einen Ladefehler', () => {
    http.expectOne(`${URL}?wochen=4`).flush('kaputt', { status: 500, statusText: 'Server Error' });
    fixture.detectChanges();

    expect(text()).toContain('konnten nicht geladen werden');
  });
});
