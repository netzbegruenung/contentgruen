import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { MatSnackBar } from '@angular/material/snack-bar';
import { BehaviorSubject } from 'rxjs';

import { environment } from '../../environments/environment';
import { AuthService, UserInfo } from '../auth/auth.service';
import { LoggingService } from './logging.service';
import { SessionService } from './session.service';
import { RueckmeldungService } from './rueckmeldung.service';

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

  const angemeldet = (userId: string): UserInfo => ({
    isAuthenticated: true,
    userId,
    userName: 'Kim',
    claims: null,
  });

  beforeEach(() => {
    anmeldung = new BehaviorSubject<UserInfo | null>(null);
    snackBar = jasmine.createSpyObj('MatSnackBar', ['open']);
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: { userInfo$: anmeldung.asObservable() } },
        { provide: MatSnackBar, useValue: snackBar },
        { provide: LoggingService, useValue: jasmine.createSpyObj('LoggingService', ['debug', 'info', 'error']) },
        { provide: SessionService, useValue: { getSessionId: () => 'sitzung-1' } },
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
});
