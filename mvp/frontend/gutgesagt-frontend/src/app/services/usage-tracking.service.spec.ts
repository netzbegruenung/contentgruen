import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';

import { environment } from '../../environments/environment';
import { UsageTrackingService } from './usage-tracking.service';
import { LoggingService } from './logging.service';

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
      ],
    });
    service = TestBed.inject(UsageTrackingService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  function antworten(id: string, count: number): void {
    http.expectOne(ADRESSE(id)).flush({ success: true, message: 'ok', usage_count: count });
  }

  it('meldet jede Kopie sofort, ohne Sitzungskennung (#446)', () => {
    service.trackContentUsage('k-1');

    const anfrage = http.expectOne(ADRESSE('k-1'));
    expect(anfrage.request.body).toEqual({});
    expect(anfrage.request.headers.has('X-Session-Id')).toBeFalse();
    anfrage.flush({ success: true, message: 'ok', usage_count: 1 });
  });

  it('meldet die kopierte Fassung eines Kommentars mit (#355)', () => {
    service.trackContentUsage('k-1', 'kurz');

    const anfrage = http.expectOne(ADRESSE('k-1'));
    expect(anfrage.request.body).toEqual({ fassung: 'kurz' });
    anfrage.flush({ success: true, message: 'ok', usage_count: 1 });
  });

  it('meldet zwei Fassungen desselben Beitrags kurz nacheinander beide', () => {
    service.trackContentUsage('k-1', 'kurz');
    service.trackContentUsage('k-1', 'lang');

    const anfragen = http.match(ADRESSE('k-1'));
    expect(anfragen.map((a) => a.request.body.fassung)).toEqual(['kurz', 'lang']);
    anfragen.forEach((a) => a.flush({ success: true, message: 'ok', usage_count: 1 }));
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

  describe('eigene Meilensteine (#351)', () => {
    const MEILENSTEINE = `${environment.baseUrl}/api/v1/usage/users/me/meilensteine`;
    const EINER = { kennung: 'nutzung-1', name: 'Erste Nutzung durch andere', art: 'wirkung', schwelle: 1, stand: 2, erreicht: true };

    it('fragt ohne Kennung im Pfad und liefert die Liste', () => {
      let ergebnis: unknown;
      service.getEigeneMeilensteine().subscribe((liste) => (ergebnis = liste));

      const anfrage = http.expectOne(MEILENSTEINE);
      expect(anfrage.request.method).toBe('GET');
      anfrage.flush({ meilensteine: [EINER] });

      expect(ergebnis).toEqual([EINER]);
    });

    it('liefert bei ausgeschalteten Punkten (404) still eine leere Liste', () => {
      let ergebnis: unknown;
      service.getEigeneMeilensteine().subscribe((liste) => (ergebnis = liste));

      http.expectOne(MEILENSTEINE).flush('weg', { status: 404, statusText: 'Not Found' });

      expect(ergebnis).toEqual([]);
      expect(TestBed.inject(LoggingService).error).not.toHaveBeenCalled();
    });

    it('liefert bei einem Fehler eine leere Liste und protokolliert ihn', () => {
      let ergebnis: unknown;
      service.getEigeneMeilensteine().subscribe((liste) => (ergebnis = liste));

      http.expectOne(MEILENSTEINE).flush('kaputt', { status: 500, statusText: 'Server Error' });

      expect(ergebnis).toEqual([]);
      expect(TestBed.inject(LoggingService).error).toHaveBeenCalled();
    });
  });

  describe('Eigene Punkte (#352)', () => {
    const PUNKTE = `${environment.baseUrl}/api/v1/usage/users/me/punkte`;
    const STAND = { tun: 2, quests: 0, wirkung: 30, gesamt: 32 };

    it('holt den eigenen Punktestand', () => {
      let ergebnis: unknown;
      service.getEigenePunkte().subscribe((stand) => (ergebnis = stand));

      const anfrage = http.expectOne(PUNKTE);
      expect(anfrage.request.method).toBe('GET');
      anfrage.flush(STAND);

      expect(ergebnis).toEqual(STAND);
    });

    it('liefert bei ausgeschalteten Punkten (404) still null', () => {
      let ergebnis: unknown = 'unberuehrt';
      service.getEigenePunkte().subscribe((stand) => (ergebnis = stand));

      http.expectOne(PUNKTE).flush('weg', { status: 404, statusText: 'Not Found' });

      expect(ergebnis).toBeNull();
      expect(TestBed.inject(LoggingService).error).not.toHaveBeenCalled();
    });

    it('liefert bei einem Fehler null und protokolliert ihn', () => {
      let ergebnis: unknown = 'unberuehrt';
      service.getEigenePunkte().subscribe((stand) => (ergebnis = stand));

      http.expectOne(PUNKTE).flush('kaputt', { status: 500, statusText: 'Server Error' });

      expect(ergebnis).toBeNull();
      expect(TestBed.inject(LoggingService).error).toHaveBeenCalled();
    });
  });

  describe('Rückmeldung „Gepostet?“ (#643)', () => {
    const GEPOSTET = `${environment.baseUrl}/api/v1/usage/users/me/gepostet`;

    function angeboten(kennung = 'kim-1'): boolean | undefined {
      let ergebnis: boolean | undefined;
      service.gepostetAngeboten(kennung).subscribe((ja) => (ergebnis = ja));
      return ergebnis;
    }

    it('bietet an, wenn der Server 200 antwortet, und fragt fuer dieselbe Kennung nicht noch einmal', () => {
      let ergebnis: boolean | undefined;
      service.gepostetAngeboten('kim-1').subscribe((ja) => (ergebnis = ja));
      const anfrage = http.expectOne(GEPOSTET);
      expect(anfrage.request.method).toBe('GET');
      anfrage.flush({ personen_diese_woche: 3 });

      expect(ergebnis).toBeTrue();
      expect(angeboten()).toBeTrue();
      http.expectNone(GEPOSTET);
    });

    it('merkt sich ein 404 (Schalter aus) still', () => {
      let ergebnis: boolean | undefined;
      service.gepostetAngeboten('kim-1').subscribe((ja) => (ergebnis = ja));
      http.expectOne(GEPOSTET).flush('weg', { status: 404, statusText: 'Not Found' });

      expect(ergebnis).toBeFalse();
      expect(angeboten()).toBeFalse();
      http.expectNone(GEPOSTET);
      expect(TestBed.inject(LoggingService).error).not.toHaveBeenCalled();
    });

    it('fragt nach einem 403 (ohne Einwilligung) beim naechsten Mal wieder', () => {
      let ergebnis: boolean | undefined;
      service.gepostetAngeboten('kim-1').subscribe((ja) => (ergebnis = ja));
      http.expectOne(GEPOSTET).flush({ detail: 'art9_einwilligung_fehlt' }, { status: 403, statusText: 'Forbidden' });

      expect(ergebnis).toBeFalse();
      service.gepostetAngeboten('kim-1').subscribe();
      http.expectOne(GEPOSTET).flush({ personen_diese_woche: 0 });
      expect(TestBed.inject(LoggingService).error).not.toHaveBeenCalled();
    });

    it('meldet per POST und liefert die Zahl der Woche', () => {
      let ergebnis: unknown;
      service.gepostetMelden('kim-1').subscribe((zahl) => (ergebnis = zahl));

      const anfrage = http.expectOne(GEPOSTET);
      expect(anfrage.request.method).toBe('POST');
      anfrage.flush({ personen_diese_woche: 7 });

      expect(ergebnis).toBe(7);
    });

    it('vergisst nach einem 403 beim Melden das gemerkte Angebot', () => {
      service.gepostetAngeboten('kim-1').subscribe();
      http.expectOne(GEPOSTET).flush({ personen_diese_woche: 1 });
      expect(service.gepostetBekannt('kim-1')).toBeTrue();
      let ergebnis: unknown;

      service.gepostetMelden('kim-1').subscribe((zahl) => (ergebnis = zahl));
      http.expectOne(GEPOSTET).flush({ detail: 'art9_einwilligung_fehlt' }, { status: 403, statusText: 'Forbidden' });

      expect(ergebnis).toBe('nicht_angeboten');
      expect(service.gepostetBekannt('kim-1')).toBeNull();
      expect(TestBed.inject(LoggingService).error).not.toHaveBeenCalled();
    });

    it('liefert null, wenn das Melden scheitert', () => {
      let ergebnis: unknown;
      service.gepostetMelden('kim-1').subscribe((zahl) => (ergebnis = zahl));

      http.expectOne(GEPOSTET).flush('kaputt', { status: 500, statusText: 'Server Error' });

      expect(ergebnis).toBeNull();
    });
  });

  describe('Sichtbarkeit der Abzeichen (#351)', () => {
    const SICHTBARKEIT = `${environment.baseUrl}/api/v1/usage/users/me/abzeichen-sichtbarkeit`;

    it('liest die Antwort', () => {
      let ergebnis: unknown;
      service.getAbzeichenSichtbarkeit().subscribe((stand) => (ergebnis = stand));
      const stand = { gefragt: false, zeigen: null, aktueller_wortlaut: { kennung: '2026-11-09-b', text: 'x', mehr_dazu: 'y' } };

      http.expectOne(SICHTBARKEIT).flush(stand);

      expect(ergebnis).toEqual(stand);
    });

    it('liefert ohne Schalter (404) still null', () => {
      let ergebnis: unknown = 'unberuehrt';
      service.getAbzeichenSichtbarkeit().subscribe((stand) => (ergebnis = stand));

      http.expectOne(SICHTBARKEIT).flush('weg', { status: 404, statusText: 'Not Found' });

      expect(ergebnis).toBeNull();
      expect(TestBed.inject(LoggingService).error).not.toHaveBeenCalled();
    });

    it('speichert per PUT mit Antwort und Wortlaut', () => {
      let ergebnis: unknown;
      service.setAbzeichenSichtbarkeit(true, '2026-11-09').subscribe((ok) => (ergebnis = ok));

      const anfrage = http.expectOne(SICHTBARKEIT);
      expect(anfrage.request.method).toBe('PUT');
      expect(anfrage.request.body).toEqual({ zeigen: true, wortlaut: '2026-11-09' });
      anfrage.flush(null, { status: 204, statusText: 'No Content' });

      expect(ergebnis).toBeTrue();
    });

    it('liefert false, wenn das Speichern scheitert', () => {
      let ergebnis: unknown;
      service.setAbzeichenSichtbarkeit(false, '2026-11-09').subscribe((ok) => (ergebnis = ok));

      http.expectOne(SICHTBARKEIT).flush('kaputt', { status: 500, statusText: 'Server Error' });

      expect(ergebnis).toBeFalse();
    });
  });

  describe('Diese Woche oft genutzt', () => {
    const OFT_GENUTZT = `${environment.baseUrl}/api/v1/usage/trending/woche`;

    it('liefert die Beitraege der Woche', () => {
      let ergebnis: unknown;
      service.getOftGenutzt().subscribe((antwort) => (ergebnis = antwort));

      http.expectOne(OFT_GENUTZT).flush({ results: [{ id: 'k-1' }] });

      expect(ergebnis).toEqual({ results: [{ id: 'k-1' }] });
    });

    it('liefert bei einem Fehler keine Beitraege, damit die Startseite den Bereich weglaesst', () => {
      let ergebnis: unknown;
      service.getOftGenutzt().subscribe((antwort) => (ergebnis = antwort));

      http.expectOne(OFT_GENUTZT).flush('kaputt', { status: 500, statusText: 'Server Error' });

      expect(ergebnis).toEqual({ results: [] });
    });
  });
});
