import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { MatSnackBar } from '@angular/material/snack-bar';
import { BehaviorSubject, Observable, of } from 'rxjs';

import { environment } from '../../environments/environment';
import { AuthService, UserInfo } from '../auth/auth.service';
import { LoggingService } from './logging.service';
import { RueckmeldungService } from './rueckmeldung.service';
import { Meilenstein } from './usage-tracking.service';
import { MeilensteinHinweisService } from '../meine-beitraege/meilenstein-hinweis.service';

/**
 * Die Rueckmeldung beim Anmelden (#349): "Seit deinem letzten Besuch wurden deine
 * Beitraege N-mal genutzt", nur in der App und nur bei N > 0.
 */
describe('RueckmeldungService', () => {
  const ADRESSE = `${environment.baseUrl}/api/v1/usage/users/me/besuch`;
  let anmeldung: BehaviorSubject<UserInfo | null>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;
  let http: HttpTestingController;
  let service: RueckmeldungService;
  let neu: Meilenstein[];
  let hinweis: { neueErreichte: () => Observable<Meilenstein[]>; zeigen: jasmine.Spy; merken: jasmine.Spy };

  const angemeldet = (userId: string): UserInfo => ({
    isAuthenticated: true,
    userId,
    userName: 'Kim',
    claims: null,
  });

  beforeEach(() => {
    anmeldung = new BehaviorSubject<UserInfo | null>(null);
    snackBar = jasmine.createSpyObj('MatSnackBar', ['open']);
    neu = [];
    hinweis = { neueErreichte: () => of(neu), zeigen: jasmine.createSpy('zeigen'), merken: jasmine.createSpy('merken') };
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: { userInfo$: anmeldung.asObservable() } },
        { provide: MatSnackBar, useValue: snackBar },
        { provide: MeilensteinHinweisService, useValue: hinweis },
        { provide: LoggingService, useValue: jasmine.createSpyObj('LoggingService', ['debug', 'info', 'error']) },
      ],
    });
    service = TestBed.inject(RueckmeldungService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    service.ngOnDestroy();
    http.verify();
  });

  it('zeigt beim Anmelden, wie oft die Beitraege seit dem letzten Besuch genutzt wurden', () => {
    service.starten();
    anmeldung.next(angemeldet('kim-1'));

    const anfrage = http.expectOne(ADRESSE);
    expect(anfrage.request.method).toBe('POST');
    anfrage.flush({ nutzung_seit_letztem_besuch: 12 });

    expect(snackBar.open).toHaveBeenCalledOnceWith(
      'Seit deinem letzten Besuch wurden deine Beiträge 12-mal genutzt',
      'OK',
      jasmine.objectContaining({ duration: jasmine.any(Number) }),
    );
  });

  it('zeigt bei 0 nichts', () => {
    service.starten();
    anmeldung.next(angemeldet('kim-1'));

    http.expectOne(ADRESSE).flush({ nutzung_seit_letztem_besuch: 0 });

    expect(snackBar.open).not.toHaveBeenCalled();
  });

  it('fragt ohne Anmeldung nicht', () => {
    service.starten();
    anmeldung.next({ isAuthenticated: false, userId: null, userName: null, claims: null });

    http.expectNone(ADRESSE);
    expect(snackBar.open).not.toHaveBeenCalled();
  });

  it('fragt je Anmeldung einmal, auch wenn die Anmeldedaten zweimal kommen', () => {
    service.starten();
    anmeldung.next(angemeldet('kim-1'));
    anmeldung.next({ ...angemeldet('kim-1'), claims: { name: 'Kim' } });

    const anfragen = http.match(ADRESSE);
    anfragen.forEach((a) => a.flush({ nutzung_seit_letztem_besuch: 0 }));
    expect(anfragen.length).toBe(1);
  });

  it('fragt nach einem Wechsel der Person erneut', () => {
    service.starten();
    anmeldung.next(angemeldet('kim-1'));
    http.expectOne(ADRESSE).flush({ nutzung_seit_letztem_besuch: 0 });

    anmeldung.next({ isAuthenticated: false, userId: null, userName: null, claims: null });
    anmeldung.next(angemeldet('bo-2'));

    const anfragen = http.match(ADRESSE);
    anfragen.forEach((a) => a.flush({ nutzung_seit_letztem_besuch: 0 }));
    expect(anfragen.length).toBe(1);
  });

  it('zeigt bei einem Fehler nichts', () => {
    service.starten();
    anmeldung.next(angemeldet('kim-1'));

    http.expectOne(ADRESSE).flush('kaputt', { status: 500, statusText: 'Server Error' });

    expect(snackBar.open).not.toHaveBeenCalled();
  });

  describe('mit neuem Meilenstein (#351, UX-Befund B6)', () => {
    const EINER: Meilenstein = {
      kennung: 'zustimmung-1', name: 'Erste Zustimmung', untertitel: 'Nicht allein', beschreibung: '',
      bild: '', bildnachweis: '', art: 'wirkung', schwelle: 1, stand: 1, erreicht: true,
    };

    it('nennt ihn beim Namen hinter der Nutzung, mit "Ansehen"', () => {
      neu = [EINER];
      service.starten();
      anmeldung.next(angemeldet('kim-1'));
      http.expectOne(ADRESSE).flush({ nutzung_seit_letztem_besuch: 3 });

      expect(hinweis.zeigen).toHaveBeenCalledOnceWith(
        'Seit deinem letzten Besuch wurden deine Beiträge 3-mal genutzt. Meilenstein erreicht: Erste Zustimmung',
      );
      expect(snackBar.open).not.toHaveBeenCalled();
      expect(hinweis.merken).toHaveBeenCalledOnceWith([EINER]);
    });

    it('nennt ihn auch ohne neue Nutzung', () => {
      neu = [EINER];
      service.starten();
      anmeldung.next(angemeldet('kim-1'));
      http.expectOne(ADRESSE).flush({ nutzung_seit_letztem_besuch: 0 });

      expect(hinweis.zeigen).toHaveBeenCalledOnceWith('Meilenstein erreicht: Erste Zustimmung');
    });
  });
});
