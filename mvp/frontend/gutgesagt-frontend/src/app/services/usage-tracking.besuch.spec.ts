import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';

import { environment } from '../../environments/environment';
import { LoggingService } from './logging.service';
import { UsageTrackingService } from './usage-tracking.service';

/** Die Zahl der Rueckmeldung bleibt fuer „Seit deinem letzten Besuch“ stehen (Nutzerfuehrung 13.11.). */
describe('UsageTrackingService.besuchStand$', () => {
  const ADRESSE = `${environment.baseUrl}/api/v1/usage/users/me/besuch`;
  let http: HttpTestingController;
  let service: UsageTrackingService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: LoggingService, useValue: jasmine.createSpyObj('LoggingService', ['debug', 'info', 'error']) },
      ],
    });
    service = TestBed.inject(UsageTrackingService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('ist null vor dem Besuch und haelt danach die Zahl, ohne erneut zu fragen', () => {
    expect(service.besuchStand$.value).toBeNull();

    let anzahl: number | null | undefined;
    service.besuchMelden().subscribe((a) => (anzahl = a));
    http.expectOne(ADRESSE).flush({ nutzung_seit_letztem_besuch: 4, neue_einwuerfe: 2, unbeantwortete_aussagen: 5 });

    expect(anzahl).toBe(4);
    expect(service.besuchStand$.value).toEqual({ nutzung_seit_letztem_besuch: 4, neue_einwuerfe: 2, unbeantwortete_aussagen: 5 });
    http.expectNone(ADRESSE);
  });

  it('vergisst die alte Zahl, sobald ein neuer Besuch gemeldet wird (Kontowechsel)', () => {
    service.besuchMelden().subscribe();
    http.expectOne(ADRESSE).flush({ nutzung_seit_letztem_besuch: 4 });

    service.besuchMelden().subscribe();
    expect(service.besuchStand$.value).toBeNull();
    http.expectOne(ADRESSE).flush({ nutzung_seit_letztem_besuch: 0 });
    expect(service.besuchStand$.value).toEqual({ nutzung_seit_letztem_besuch: 0 });
  });

  it('bleibt bei einem Fehler null', () => {
    service.besuchMelden().subscribe();
    http.expectOne(ADRESSE).flush('kaputt', { status: 502, statusText: 'Bad Gateway' });

    expect(service.besuchStand$.value).toBeNull();
  });
});
