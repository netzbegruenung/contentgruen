import { DestroyRef } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { MatSnackBar } from '@angular/material/snack-bar';
import { DefaultUrlSerializer, NavigationEnd, Router } from '@angular/router';
import { BehaviorSubject, Subject } from 'rxjs';
import { Art9EinwilligungService } from '../services/art9-einwilligung.service';
import { AuthService, UserInfo } from './auth.service';
import { ANLASS_PARAM, NACH_ANMELDUNG_HINWEIS } from './anmeldeanlass';
import { hinweisNachAnmeldung } from './nach-anmeldung';

// Nach der Anmeldung aus der Daumen-Snackbar: ein Satz, dass Abstimmen jetzt geht (Persona-Test)
describe('hinweisNachAnmeldung', () => {
  let events: Subject<unknown>;
  let userInfo: BehaviorSubject<UserInfo | null>;
  let geklaert: BehaviorSubject<string | null>;
  let navigate: jasmine.Spy;
  let snackBar: jasmine.SpyObj<MatSnackBar>;
  let hooks: Array<() => void>;

  const angemeldet: UserInfo = { isAuthenticated: true, userId: 'u1', userName: 'Test', claims: null };
  const besucher: UserInfo = { isAuthenticated: false, userId: null, userName: null, claims: null };
  const zurueck = `/result?searchQuery=Heizung&${ANLASS_PARAM}=abstimmen`;

  beforeEach(() => {
    events = new Subject();
    userInfo = new BehaviorSubject<UserInfo | null>(null);
    geklaert = new BehaviorSubject<string | null>(null);
    snackBar = jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']);
    navigate = jasmine.createSpy('navigate').and.resolveTo(true);
    const serializer = new DefaultUrlSerializer();
    TestBed.configureTestingModule({
      providers: [
        { provide: Router, useValue: { events, navigate, parseUrl: (u: string) => serializer.parse(u) } },
        { provide: MatSnackBar, useValue: snackBar },
        { provide: AuthService, useValue: { userInfo$: userInfo } },
        { provide: Art9EinwilligungService, useValue: { geklaert$: geklaert } },
      ],
    });
    hooks = [];
    const destroyRef = { onDestroy: (h: () => void) => hooks.push(h) } as unknown as DestroyRef;
    TestBed.runInInjectionContext(() => hinweisNachAnmeldung(destroyRef));
  });

  afterEach(() => hooks.forEach((h) => h()));

  function navigiert(url: string): void {
    events.next(new NavigationEnd(1, url, url));
  }

  const parameterEntfernt = () =>
    expect(navigate).toHaveBeenCalledWith([], {
      queryParams: { [ANLASS_PARAM]: null },
      queryParamsHandling: 'merge',
      replaceUrl: true,
    });

  it('sagt Angemeldeten nach der Einwilligung, dass sie jetzt abstimmen koennen, und nimmt den Parameter weg', () => {
    navigiert(zurueck);
    userInfo.next(angemeldet);
    expect(snackBar.open).not.toHaveBeenCalled();

    geklaert.next('u1');

    expect(snackBar.open).toHaveBeenCalledOnceWith(NACH_ANMELDUNG_HINWEIS.abstimmen, 'OK', jasmine.any(Object));
    parameterEntfernt();
  });

  it('zeigt den Satz nur einmal, auch wenn das Rueckkehrziel noch einmal ausgefuehrt wird', () => {
    userInfo.next(angemeldet);
    geklaert.next('u1');
    navigiert(zurueck);
    navigiert(zurueck);

    expect(snackBar.open).toHaveBeenCalledTimes(1);
  });

  it('ohne Anmeldung zurueck: kein Satz, aber der Parameter verschwindet', () => {
    userInfo.next(besucher);
    navigiert(zurueck);

    expect(snackBar.open).not.toHaveBeenCalled();
    parameterEntfernt();
  });

  it('ohne Parameter passiert nichts', () => {
    userInfo.next(angemeldet);
    geklaert.next('u1');
    navigiert('/result?searchQuery=Heizung');

    expect(snackBar.open).not.toHaveBeenCalled();
    expect(navigate).not.toHaveBeenCalled();
  });

  it('ein unbekannter Anlass bringt keinen Satz', () => {
    userInfo.next(angemeldet);
    geklaert.next('u1');
    navigiert(`/result?${ANLASS_PARAM}=irgendwas`);

    expect(snackBar.open).not.toHaveBeenCalled();
    parameterEntfernt();
  });
});
