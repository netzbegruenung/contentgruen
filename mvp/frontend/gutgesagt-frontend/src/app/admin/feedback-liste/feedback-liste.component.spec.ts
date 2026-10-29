import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { FeedbackListeComponent } from './feedback-liste.component';
import { environment } from '../../../environments/environment';

const URL = `${environment.baseUrl}/api/v1/feedback`;

describe('FeedbackListeComponent', () => {
  let fixture: ComponentFixture<FeedbackListeComponent>;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [FeedbackListeComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(FeedbackListeComponent);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  });

  afterEach(() => http.verify());

  function text(): string {
    return (fixture.nativeElement as HTMLElement).textContent ?? '';
  }

  it('zeigt Tag, Text und Kontakt, wie geliefert', () => {
    http.expectOne(URL).flush({
      aufbewahrung_tage: 180,
      eintraege: [
        { id: 'a', text: 'Kopieren klappt mobil nicht', kontakt: 'anna@example.org', eingegangen_am: '2026-10-27' },
        { id: 'b', text: 'Gefällt mir', kontakt: null, eingegangen_am: '2026-10-26' },
      ],
    });
    fixture.detectChanges();

    const zeilen = Array.from(
      (fixture.nativeElement as HTMLElement).querySelectorAll('[data-testid="feedback-eintrag"]')
    ).map((z) => Array.from(z.querySelectorAll('td')).map((td) => td.textContent?.trim()));

    expect(zeilen).toEqual([
      ['27.10.2026', 'Kopieren klappt mobil nicht', 'anna@example.org'],
      ['26.10.2026', 'Gefällt mir', '–'],
    ]);
    expect(text()).toContain('180 Tagen');
  });

  it('sagt, wenn noch kein Feedback da ist', () => {
    http.expectOne(URL).flush({ aufbewahrung_tage: 180, eintraege: [] });
    fixture.detectChanges();

    expect(text()).toContain('Noch kein Feedback');
  });

  it('meldet einen Ladefehler', () => {
    http.expectOne(URL).flush('kaputt', { status: 500, statusText: 'Server Error' });
    fixture.detectChanges();

    expect(text()).toContain('konnte nicht geladen werden');
  });
});
