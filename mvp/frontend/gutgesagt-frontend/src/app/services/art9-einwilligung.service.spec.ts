import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { NavigationEnd, Router } from '@angular/router';
import { BehaviorSubject, Subject } from 'rxjs';

import { environment } from '../../environments/environment';
import { AuthService, UserInfo } from '../auth/auth.service';
import { Art9EinwilligungService, Art9EinwilligungStand, wortlautDatum } from './art9-einwilligung.service';

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

  it('einwilligen schickt die Kennung, widerrufen loescht', () => {
    service.einwilligen('2026-11-05-b').subscribe();
    const post = http.expectOne({ method: 'POST', url: ADRESSE });
    expect(post.request.body).toEqual({ wortlaut: '2026-11-05-b' });
    post.flush(null);

    service.widerrufen().subscribe();
    http.expectOne({ method: 'DELETE', url: ADRESSE }).flush(null);
  });
});
