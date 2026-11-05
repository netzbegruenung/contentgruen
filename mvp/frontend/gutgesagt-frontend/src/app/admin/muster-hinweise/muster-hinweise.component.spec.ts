import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { MusterHinweiseComponent } from './muster-hinweise.component';
import { environment } from '../../../environments/environment';

const URL = `${environment.baseUrl}/api/v1/metrics/muster-hinweise`;

describe('MusterHinweiseComponent', () => {
  let fixture: ComponentFixture<MusterHinweiseComponent>;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MusterHinweiseComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(MusterHinweiseComponent);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  });

  afterEach(() => http.verify());

  function text(): string {
    return (fixture.nativeElement as HTMLElement).textContent ?? '';
  }

  it('zeigt die Kontenpaare mit Namen, Kennung, Tagen und Zeitraum', () => {
    http.expectOne(URL).flush({
      aktiv: true,
      frist_tage: 56,
      hinweise: [
        {
          konto_a: 'bo-2',
          name_a: null,
          konto_b: 'kim-1',
          name_b: 'Kim A.',
          tage: 3,
          erster_tag: '2026-10-20',
          letzter_tag: '2026-10-29',
        },
      ],
    });
    fixture.detectChanges();

    const zeilen = Array.from(
      (fixture.nativeElement as HTMLElement).querySelectorAll('[data-testid="muster-hinweis"]')
    ).map((z) => Array.from(z.querySelectorAll('td')).map((td) => td.textContent?.trim()));

    expect(zeilen).toEqual([['bo-2', 'Kim A. (kim-1)', '3', '2026-10-20 – 2026-10-29']]);
    expect(text()).toContain('56 Tage');
  });

  it('sagt, wenn Punkte ausgeschaltet sind', () => {
    http.expectOne(URL).flush({ aktiv: false, frist_tage: 56, hinweise: [] });
    fixture.detectChanges();

    expect(text()).toContain('Punkte sind ausgeschaltet');
    expect(text()).not.toContain('Kein auffälliges Muster');
  });

  it('sagt, wenn es kein Muster gibt', () => {
    http.expectOne(URL).flush({ aktiv: true, frist_tage: 56, hinweise: [] });
    fixture.detectChanges();

    expect(text()).toContain('Kein auffälliges Muster');
  });

  it('meldet einen Ladefehler', () => {
    http.expectOne(URL).flush('kaputt', { status: 500, statusText: 'Server Error' });
    fixture.detectChanges();

    expect(text()).toContain('konnten nicht geladen werden');
  });
});
