import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { NavigationEnd, Router } from '@angular/router';
import { BehaviorSubject, Subject } from 'rxjs';

import { environment } from '../../environments/environment';
import { AuthService, UserInfo } from '../auth/auth.service';
import {
  Art9EinwilligungService,
  Art9EinwilligungStand,
  ALTER_OHNE_SCHLUESSEL,
  WORTLAUT_LABEL_MAX,
  einwilligungFehlt,
  wortlautDatum,
  wortlautErsterSatz,
  zurEinwilligungUmleiten,
} from './art9-einwilligung.service';
import { Art9EinwilligungZustand } from './art9-einwilligung-zustand';
import { entwurfHolen, entwurfSichern } from '../einwilligung/entwurf-vor-einwilligung';

/** Nach dem Anmelden ohne Art.-9-Einwilligung auf /einwilligung fuehren (#489). */
describe('Art9EinwilligungService', () => {
  const ADRESSE = `${environment.baseUrl}/api/v1/art9-einwilligung`;
  let anmeldung: BehaviorSubject<UserInfo | null>;
  let router: { url: string; navigate: jasmine.Spy; events: Subject<unknown>; getCurrentNavigation: jasmine.Spy };
  let http: HttpTestingController;
  let service: Art9EinwilligungService;

  const angemeldet = (userId: string): UserInfo => ({
    isAuthenticated: true,
    userId,
    userName: 'Kim',
    claims: null,
  });

  const stand = (eingewilligt: boolean): Art9EinwilligungStand => ({
    eingewilligt,
    wortlaut: eingewilligt ? '2026-11-05-b' : null,
    eingewilligt_am: null,
    widerrufen_am: null,
    aktueller_wortlaut: { kennung: '2026-11-05-b', text: '…' },
  });

  beforeEach(() => {
    localStorage.removeItem(ALTER_OHNE_SCHLUESSEL);
    anmeldung = new BehaviorSubject<UserInfo | null>(null);
    router = {
      url: '/fangkorb',
      navigate: jasmine.createSpy('navigate'),
      events: new Subject<unknown>(),
      getCurrentNavigation: jasmine.createSpy('getCurrentNavigation').and.returnValue(null),
    };
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: { userInfo$: anmeldung.asObservable() } },
        { provide: Router, useValue: router },
      ],
    });
    service = TestBed.inject(Art9EinwilligungService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    service.ngOnDestroy();
    http.verify();
    localStorage.removeItem(ALTER_OHNE_SCHLUESSEL);
  });

  it('fragt fuer Besucher nicht', () => {
    service.starten();
    anmeldung.next({ isAuthenticated: false, userId: null, userName: null, claims: null });

    http.expectNone(ADRESSE);
    expect(router.navigate).not.toHaveBeenCalled();
  });

  it('fuehrt ohne Einwilligung auf /einwilligung, mit Rueckweg', () => {
    service.starten();
    anmeldung.next(angemeldet('kim'));

    http.expectOne(ADRESSE).flush(stand(false));

    expect(router.navigate).toHaveBeenCalledWith(['/einwilligung'], { queryParams: { returnUrl: '/fangkorb' } });
  });

  it('wartet eine laufende Navigation ab, damit der Rueckweg dorthin fuehrt', () => {
    router.url = '/login';
    router.getCurrentNavigation.and.returnValue({});
    service.starten();
    anmeldung.next(angemeldet('kim'));
    http.expectOne(ADRESSE).flush(stand(false));
    expect(router.navigate).not.toHaveBeenCalled();

    router.url = '/beitrag/123';
    router.events.next(new NavigationEnd(1, '/beitrag/123', '/beitrag/123'));

    expect(router.navigate).toHaveBeenCalledWith(['/einwilligung'], { queryParams: { returnUrl: '/beitrag/123' } });
  });

  it('laesst mit Einwilligung in Ruhe', () => {
    service.starten();
    anmeldung.next(angemeldet('kim'));

    http.expectOne(ADRESSE).flush(stand(true));

    expect(router.navigate).not.toHaveBeenCalled();
  });

  // Ob ein frueherer Wortlaut zaehlt, entscheidet das Backend (GELTENDE_WORTLAUTE); das
  // Frontend folgt nur ``eingewilligt``. #644: 2026-11-10 fragte niemanden neu.
  it('laesst in Ruhe, wer einem aelteren Wortlaut zugestimmt hat, solange das Backend eingewilligt meldet', () => {
    service.starten();
    anmeldung.next(angemeldet('kim'));

    http.expectOne(ADRESSE).flush({
      ...stand(true),
      wortlaut: '2026-11-05-b',
      aktueller_wortlaut: { kennung: '2026-11-10', text: '…' },
    });

    expect(router.navigate).not.toHaveBeenCalled();
  });

  // 2026-11-13: Nur dieser Wortlaut zaehlt; wer einem frueheren zugestimmt hat, wird neu gefragt
  it('fragt neu, wenn das Backend eine fruehere Einwilligung nicht mehr zaehlt', () => {
    service.starten();
    anmeldung.next(angemeldet('kim'));

    http.expectOne(ADRESSE).flush({
      ...stand(false),
      wortlaut: '2026-11-12',
      eingewilligt_am: '2026-11-12T09:30:00Z',
      aktueller_wortlaut: { kennung: '2026-11-13', text: '…' },
    });

    expect(router.navigate).toHaveBeenCalledWith(['/einwilligung'], { queryParams: { returnUrl: '/fangkorb' } });
  });

  it('meldet die Person als geklaert, sobald sie eingewilligt hat (#587)', () => {
    service.starten();
    anmeldung.next(angemeldet('kim'));
    expect(service.geklaert()).toBeNull();

    http.expectOne(ADRESSE).flush(stand(true));

    expect(service.geklaert()).toBe('kim');
  });

  it('meldet ohne Einwilligung erst nach dem Einwilligen geklaert (#587)', () => {
    service.starten();
    anmeldung.next(angemeldet('kim'));
    http.expectOne(ADRESSE).flush(stand(false));
    expect(service.geklaert()).toBeNull();

    service.einwilligen('2026-11-05-b').subscribe();
    http.expectOne({ method: 'POST', url: ADRESSE }).flush(null);

    expect(service.geklaert()).toBe('kim');
  });

  it('vergisst die Klaerung beim Abmelden (#587)', () => {
    service.starten();
    anmeldung.next(angemeldet('kim'));
    http.expectOne(ADRESSE).flush(stand(true));

    anmeldung.next({ isAuthenticated: false, userId: null, userName: null, claims: null });

    expect(service.geklaert()).toBeNull();
  });

  it('vergisst die Klaerung nach dem Widerruf (#587)', () => {
    service.starten();
    anmeldung.next(angemeldet('kim'));
    http.expectOne(ADRESSE).flush(stand(true));

    service.widerrufen().subscribe();
    http.expectOne({ method: 'DELETE', url: ADRESSE }).flush(null);

    expect(service.geklaert()).toBeNull();
  });

  it('meldet geklaert, wenn der Stand nicht kommt (#587)', () => {
    service.starten();
    anmeldung.next(angemeldet('kim'));

    http.expectOne(ADRESSE).flush(null, { status: 500, statusText: 'Fehler' });

    expect(service.geklaert()).toBe('kim');
  });

  it('fragt einmal je Person, auch wenn die Anmeldedaten zweimal kommen', () => {
    service.starten();
    anmeldung.next(angemeldet('kim'));
    http.expectOne(ADRESSE).flush(stand(true));
    anmeldung.next(angemeldet('kim'));

    http.expectNone(ADRESSE);
    expect(router.navigate).not.toHaveBeenCalled();
  });

  it('leitet von der Datenschutzerklaerung aus nicht um', () => {
    router.url = '/datenschutz';
    service.starten();
    anmeldung.next(angemeldet('kim'));

    http.expectOne(ADRESSE).flush(stand(false));

    expect(router.navigate).not.toHaveBeenCalled();
  });

  it('leitet nicht um, wenn der Stand nicht kommt', () => {
    service.starten();
    anmeldung.next(angemeldet('kim'));

    http.expectOne(ADRESSE).flush(null, { status: 500, statusText: 'Fehler' });

    expect(router.navigate).not.toHaveBeenCalled();
  });

  it('wortlautDatum liest das Stand-Datum aus der Kennung, auch mit Suffix', () => {
    expect(wortlautDatum('2026-11-05')).toBe('2026-11-05');
    expect(wortlautDatum('2026-11-05-b')).toBe('2026-11-05');
    expect(wortlautDatum('kein-datum')).toBeNull();
    expect(wortlautDatum(null)).toBeNull();
  });

  // #620: Label am Haekchen ist der erste Satz, unveraendert; "Abs. 2 lit. a" trennt nicht
  it('wortlautErsterSatz nimmt den ersten Satz unveraendert und trennt nicht an Abkuerzungen', () => {
    const text =
      'Ich willige ausdrücklich ein, dass X meine Mitwirkung verarbeitet (Art. 9 Abs. 2 lit. a DSGVO). ' +
      'Das betrifft Beiträge. Ich kann widerrufen.';
    expect(wortlautErsterSatz(text)).toBe(
      'Ich willige ausdrücklich ein, dass X meine Mitwirkung verarbeitet (Art. 9 Abs. 2 lit. a DSGVO).',
    );
    expect(text.startsWith(wortlautErsterSatz(text))).toBeTrue();
  });

  // Kopie des aktuellen Wortlauts 2026-11-13 (domain/art9_einwilligung.py), Anfang und
  // zweiter Satz: Aendert sich der Wortlaut, zeigt dieser Test, ob der Schnitt noch passt.
  it('wortlautErsterSatz schneidet den aktuellen Wortlaut nach dem Art.-9-Satz', () => {
    const ersterSatz =
      'Ich willige ausdrücklich ein, dass Gut gesagt meine Mitwirkung verarbeitet, auch wenn sich daraus ' +
      'auf meine politische Meinung schließen lässt (Art. 9 Abs. 2 lit. a DSGVO).';
    const text = ersterSatz + ' Das betrifft Beiträge, Einwürfe, Sätze und Bewertungen, die ich mit meinem Konto speichere.';
    expect(wortlautErsterSatz(text)).toBe(ersterSatz);
  });

  it('wortlautErsterSatz gibt ohne Satzende oder bei zu langem ersten Satz den ganzen Text', () => {
    expect(wortlautErsterSatz('Nur ein Satz ohne Folgesatz.')).toBe('Nur ein Satz ohne Folgesatz.');
    const lang = 'a'.repeat(WORTLAUT_LABEL_MAX + 1) + '. Zweiter Satz.';
    expect(wortlautErsterSatz(lang)).toBe(lang);
  });

  it('einwilligen schickt die Kennung, widerrufen loescht', () => {
    service.einwilligen('2026-11-05-b').subscribe();
    const post = http.expectOne({ method: 'POST', url: ADRESSE });
    expect(post.request.body).toEqual({ wortlaut: '2026-11-05-b' });
    post.flush(null);

    service.widerrufen().subscribe();
    http.expectOne({ method: 'DELETE', url: ADRESSE }).flush(null);
  });
  // UX-Review B2: nur beim ersten Anmelden umleiten, nicht nach einer Entscheidung
  describe('nicht draengen (B2)', () => {
    const widerrufen = (): Art9EinwilligungStand => ({
      ...stand(false),
      wortlaut: '2026-11-05-b',
      eingewilligt_am: '2026-11-05T09:00:00Z',
      widerrufen_am: '2026-11-06T09:00:00Z',
    });

    it('leitet nach einem Widerruf nicht um', () => {
      service.starten();
      anmeldung.next(angemeldet('kim'));

      http.expectOne(ADRESSE).flush(widerrufen());

      expect(router.navigate).not.toHaveBeenCalled();
    });

    it('leitet nicht um, wer laut Server ohne Einwilligung weitergegangen ist', () => {
      service.starten();
      anmeldung.next(angemeldet('kim'));

      http.expectOne(ADRESSE).flush({ ...stand(false), ohne_wortlaut: '2026-11-05-b' });

      expect(router.navigate).not.toHaveBeenCalled();
    });

    it('merkt sich "ohne" am Konto per POST, nicht im Browser', () => {
      const setItem = spyOn(Storage.prototype, 'setItem').and.callThrough();

      service.ohneMerken('2026-11-05-b').subscribe();

      const anfrage = http.expectOne({ method: 'POST', url: `${ADRESSE}/ohne` });
      expect(anfrage.request.body).toEqual({ wortlaut: '2026-11-05-b' });
      anfrage.flush(null);
      expect(setItem).not.toHaveBeenCalled();
    });

    it('raeumt einen alten Eintrag im localStorage beim Start weg', () => {
      localStorage.setItem(ALTER_OHNE_SCHLUESSEL, '2026-11-05-b');

      service.starten();

      expect(localStorage.getItem(ALTER_OHNE_SCHLUESSEL)).toBeNull();
    });

    it('holt den Stand neu, wenn der Tab wieder sichtbar wird (Einwilligung aus einem anderen Tab)', () => {
      const zustand = TestBed.inject(Art9EinwilligungZustand);
      service.starten();
      anmeldung.next(angemeldet('kim'));
      http.expectOne(ADRESSE).flush({ ...stand(false), ohne_wortlaut: '2026-11-05-b' });
      expect(zustand.wert).toBe('fehlt');

      document.dispatchEvent(new Event('visibilitychange'));
      http.expectOne(ADRESSE).flush(stand(true));

      expect(zustand.wert).toBe('eingewilligt');
      expect(router.navigate).not.toHaveBeenCalled();
    });

    it('nimmt die Klaerung zurueck, wenn ein anderer Tab widerrufen hat', () => {
      service.starten();
      anmeldung.next(angemeldet('kim'));
      http.expectOne(ADRESSE).flush(stand(true));
      expect(service.geklaert()).toBe('kim');

      document.dispatchEvent(new Event('visibilitychange'));
      http.expectOne(ADRESSE).flush({ ...stand(false), widerrufen_am: '2026-11-14T09:00:00Z' });

      expect(service.geklaert()).toBeNull();
      expect(TestBed.inject(Art9EinwilligungZustand).wert).toBe('fehlt');
    });

    it('setzt den Zustand fuer Formulare: fehlt, eingewilligt, nach dem Abmelden unbekannt', () => {
      const zustand = TestBed.inject(Art9EinwilligungZustand);
      service.starten();
      anmeldung.next(angemeldet('kim'));
      http.expectOne(ADRESSE).flush(stand(false));
      expect(zustand.wert).toBe('fehlt');

      service.einwilligen('2026-11-05-b').subscribe();
      http.expectOne({ method: 'POST', url: ADRESSE }).flush(null);
      expect(zustand.wert).toBe('eingewilligt');

      service.widerrufen().subscribe();
      http.expectOne({ method: 'DELETE', url: ADRESSE }).flush(null);
      expect(zustand.wert).toBe('fehlt');

      anmeldung.next(null);
      expect(zustand.wert).toBe('unbekannt');
    });

    it('zurEinwilligungUmleiten: erstes Mal ja, nach Entscheidung nein, neuer Wortlaut nach frueherer Einwilligung einmal ja', () => {
      const neu = stand(false);
      expect(zurEinwilligungUmleiten(neu)).toBeTrue();
      expect(zurEinwilligungUmleiten({ ...neu, ohne_wortlaut: '2026-11-05-b' })).toBeFalse();
      expect(zurEinwilligungUmleiten(stand(true))).toBeFalse();
      expect(zurEinwilligungUmleiten(widerrufen())).toBeFalse();

      const frueher: Art9EinwilligungStand = {
        ...stand(false),
        wortlaut: '2026-11-12',
        eingewilligt_am: '2026-11-12T09:00:00Z',
        aktueller_wortlaut: { kennung: '2026-11-13', text: '…' },
      };
      // Frueher schon einmal ohne weiter (zu einem aelteren Wortlaut): zum neuen trotzdem fragen
      expect(zurEinwilligungUmleiten({ ...frueher, ohne_wortlaut: '2026-11-10' })).toBeTrue();
      // Zum aktuellen schon ohne weiter: nicht noch einmal
      expect(zurEinwilligungUmleiten({ ...frueher, ohne_wortlaut: '2026-11-13' })).toBeFalse();
    });
  });

  it('raeumt Entwuerfe beim App-Start auf und loescht sie beim Abmelden und Kontowechsel', () => {
    entwurfSichern('/einwerfen', 'von kim', 'kim');
    entwurfSichern('/fangkorb', 'von alex', 'alex');
    service.starten();
    anmeldung.next(angemeldet('kim'));
    http.expectOne(ADRESSE).flush(stand(true));
    expect(entwurfHolen('/fangkorb', 'alex')).toBeUndefined();
    expect(entwurfHolen('/einwerfen', 'kim')).toBe('von kim');

    entwurfSichern('/einwerfen', 'von kim', 'kim');
    anmeldung.next(angemeldet('alex'));
    http.expectOne(ADRESSE).flush(stand(true));
    expect(entwurfHolen('/einwerfen', 'kim')).toBeUndefined();

    entwurfSichern('/einwerfen', 'von alex', 'alex');
    anmeldung.next(null);
    expect(entwurfHolen('/einwerfen', 'alex')).toBeUndefined();
  });

  it('einwilligungFehlt erkennt nur 403 mit Kennzeichen', () => {
    expect(einwilligungFehlt({ status: 403, error: { detail: 'art9_einwilligung_fehlt' } })).toBeTrue();
    expect(einwilligungFehlt({ status: 403, error: { detail: 'anderes' } })).toBeFalse();
    expect(einwilligungFehlt({ status: 500 })).toBeFalse();
    expect(einwilligungFehlt(new Error('x'))).toBeFalse();
    expect(einwilligungFehlt(null)).toBeFalse();
  });
});
