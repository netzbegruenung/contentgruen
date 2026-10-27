import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';

import { environment } from '../../environments/environment';
import { UsageTrackingService } from './usage-tracking.service';
import { LoggingService } from './logging.service';
import { SessionService } from './session.service';

/**
 * Der Zaehler soll jede Kopie melden - ausser dem Doppeltipp, der dieselbe Kopie
 * zweimal meldet. Frueher verschluckte ein `distinctUntilChanged` jede Wiederholung
 * desselben Beitrags, und ein `debounceTime` liess von zwei schnell
 * aufeinanderfolgenden Beitraegen nur einen durch.
 */
describe('UsageTrackingService', () => {
  const ADRESSE = (id: string) => `${environment.baseUrl}/api/v1/usage/content/${id}/usage`;
  let service: UsageTrackingService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: LoggingService, useValue: jasmine.createSpyObj('LoggingService', ['debug', 'info', 'error']) },
        { provide: SessionService, useValue: { getSessionId: () => 'sitzung-1' } },
      ],
    });
    service = TestBed.inject(UsageTrackingService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  function antworten(id: string, count: number): void {
    http.expectOne(ADRESSE(id)).flush({ success: true, message: 'ok', usage_count: count });
  }

  it('meldet jede Kopie sofort', () => {
    service.trackContentUsage('k-1');

    const anfrage = http.expectOne(ADRESSE('k-1'));
    expect(anfrage.request.body).toEqual({ session_id: 'sitzung-1' });
    anfrage.flush({ success: true, message: 'ok', usage_count: 1 });
  });

  it('meldet zwei verschiedene Beitraege kurz nacheinander beide', () => {
    service.trackContentUsage('k-1');
    service.trackContentUsage('k-2');

    antworten('k-1', 1);
    antworten('k-2', 1);
    expect(true).withContext('beide Meldungen sind rausgegangen').toBeTrue();
  });

  it('meldet denselben Beitrag nach Ablauf der Sperre wieder', () => {
    const start = Date.now();
    spyOn(Date, 'now').and.returnValue(start);
    service.trackContentUsage('k-1');
    antworten('k-1', 1);

    // Innerhalb von zwei Sekunden: derselbe Tipp, keine zweite Meldung.
    service.trackContentUsage('k-1');
    http.expectNone(ADRESSE('k-1'));

    (Date.now as jasmine.Spy).and.returnValue(start + 2500);
    service.trackContentUsage('k-1');

    const zweite = http.expectOne(ADRESSE('k-1'));
    expect(zweite.request.method).toBe('POST');
    zweite.flush({ success: true, message: 'ok', usage_count: 2 });
  });

  describe('eigene Nutzungsstatistik', () => {
    // Die Kennung steht nicht im Pfad, sonst landete sie in den Zugriffslogs der
    // Webserver davor; das BFF reicht die Person aus der Anmeldung weiter (#284).
    const EIGENE = `${environment.baseUrl}/api/v1/usage/users/me/usage-stats`;

    it('fragt ohne Kennung im Pfad', () => {
      let ergebnis: unknown;
      service.getEigeneNutzungsstatistik().subscribe(stats => (ergebnis = stats));

      const anfrage = http.expectOne(EIGENE);
      expect(anfrage.request.method).toBe('GET');
      const stats = { user_id: 'kim-1', unique_contents_contributed: 2, total_usage_count: 7, top_content: [] };
      anfrage.flush(stats);

      expect(ergebnis).toEqual(stats);
    });

    it('liefert bei einem Fehler null, damit die Seite ihre eigene Summe zeigt', () => {
      let ergebnis: unknown = 'unberuehrt';
      service.getEigeneNutzungsstatistik().subscribe(stats => (ergebnis = stats));

      http.expectOne(EIGENE).flush('kaputt', { status: 500, statusText: 'Server Error' });

      expect(ergebnis).toBeNull();
    });
  });
});
