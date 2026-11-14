import { DestroyRef } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { NavigationEnd, Router } from '@angular/router';
import { BehaviorSubject, Subject } from 'rxjs';
import { AuthService, UserInfo } from '../auth/auth.service';
import { Art9EinwilligungService } from '../services/art9-einwilligung.service';
import { HOME_HINWEIS_MERKER } from '../shared/geraetespeicher-schalter';
import { HOME_BILDSCHIRM_MOEGLICH } from './home-bildschirm';
import { RundgangService } from './rundgang.service';
import { HOME_ANGEBOT, WILLKOMMEN } from './rundgang-daten';
import { HOME_HINWEIS_SCHLUESSEL, MITMACHEN_SCHLUESSEL, WILLKOMMEN_SCHLUESSEL } from './rundgang-merker';

/** Hinweis „Gut gesagt als App“ auf iPhone und iPad im selben Band wie das Willkommen. */
describe('RundgangService: Hinweis Home-Bildschirm', () => {
  const SCHLUESSEL = [WILLKOMMEN_SCHLUESSEL, MITMACHEN_SCHLUESSEL, HOME_HINWEIS_SCHLUESSEL];
  const besucher: UserInfo = { isAuthenticated: false, userId: null, userName: null, claims: null };
  const angemeldet: UserInfo = { isAuthenticated: true, userId: 'u1', userName: 'Test', claims: null };

  let events: Subject<unknown>;
  let router: { url: string; events: Subject<unknown> };
  let userInfo: BehaviorSubject<UserInfo | null>;
  let geklaert: BehaviorSubject<string | null>;
  let ios: boolean;
  let schalter: boolean;

  function aufraeumen(): void {
    SCHLUESSEL.forEach((s) => localStorage.removeItem(s));
  }

  beforeEach(() => {
    aufraeumen();
    ios = true;
    schalter = true;
    events = new Subject();
    router = { url: '/search', events };
    userInfo = new BehaviorSubject<UserInfo | null>(besucher);
    geklaert = new BehaviorSubject<string | null>(null);
    TestBed.configureTestingModule({
      providers: [
        { provide: Router, useValue: router },
        { provide: AuthService, useValue: { userInfo$: userInfo } },
        { provide: Art9EinwilligungService, useValue: { geklaert$: geklaert, geklaert: () => geklaert.value } },
        { provide: HOME_BILDSCHIRM_MOEGLICH, useValue: () => ios },
        { provide: HOME_HINWEIS_MERKER, useFactory: () => schalter },
      ],
    });
  });

  afterEach(aufraeumen);

  /** Ein Besuch: eine frische Instanz, wie nach dem Neuladen der App. */
  function besuch(): RundgangService {
    const service = TestBed.runInInjectionContext(() => new RundgangService());
    service.beobachten({ onDestroy: () => undefined } as unknown as DestroyRef);
    return service;
  }

  function navigiert(url: string): void {
    router.url = url;
    events.next(new NavigationEnd(1, url, url));
  }

  /** Willkommen in einem früheren Besuch beantwortet: sein Vermerk steht im Speicher. */
  function willkommenErledigt(): void {
    localStorage.setItem(WILLKOMMEN_SCHLUESSEL, '1');
  }

  /** Alles, was die App gerade im Speicher hat, außer dem, was der Test selbst hineinlegt. */
  function eigeneEintraege(): string[] {
    return Object.keys(localStorage).filter((k) => k.startsWith('gutgesagt-') && k !== WILLKOMMEN_SCHLUESSEL);
  }

  it('erscheint nicht, solange das Willkommen offen ist: das kommt zuerst', () => {
    const service = besuch();
    navigiert('/search');
    expect(service.band()).toBe(WILLKOMMEN);
  });

  it('erscheint auf der Startseite, wenn das Willkommen schon beantwortet ist', () => {
    willkommenErledigt();
    const service = besuch();
    navigiert('/search');
    expect(service.band()).toBe(HOME_ANGEBOT);
  });

  it('erscheint auch, wenn statt des Willkommens Mitmachen beantwortet ist', () => {
    localStorage.setItem(MITMACHEN_SCHLUESSEL, '1');
    const service = besuch();
    navigiert('/search');
    expect(service.band()).toBe(HOME_ANGEBOT);
  });

  it('nach dem Willkommen nicht gleich im selben Besuch, aber beim nächsten', () => {
    const erster = besuch();
    navigiert('/search');
    expect(erster.band()).toBe(WILLKOMMEN);
    erster.bandBeantworten(false);
    expect(erster.band()).toBeNull();
    const zweiter = besuch();
    navigiert('/search');
    expect(zweiter.band()).toBe(HOME_ANGEBOT);
  });

  it('angemeldet erst nach der Einwilligung', () => {
    willkommenErledigt();
    userInfo.next(angemeldet);
    const service = besuch();
    navigiert('/search');
    expect(service.band()).toBeNull();
    geklaert.next('u1');
    expect(service.band()).toBe(HOME_ANGEBOT);
  });

  it('die Anmeldung allein reicht nicht: ohne Vermerk zuerst das Willkommen', () => {
    userInfo.next(angemeldet);
    geklaert.next('u1');
    const service = besuch();
    navigiert('/search');
    expect(service.band()).toBe(WILLKOMMEN);
  });

  it('steht nur auf der Startseite, nicht über den Treffern', () => {
    willkommenErledigt();
    const service = besuch();
    navigiert('/result?searchQuery=x');
    expect(service.band()).toBeNull();
  });

  it('schreibt beim Anzeigen nichts in den Speicher, erst mit „Ausblenden“', () => {
    willkommenErledigt();
    const sitzungVorher = sessionStorage.length;
    const cookiesVorher = document.cookie;
    const schreiben = spyOn(Storage.prototype, 'setItem').and.callThrough();
    const service = besuch();
    navigiert('/search');
    expect(service.band()).toBe(HOME_ANGEBOT);
    expect(schreiben).not.toHaveBeenCalled();
    expect(eigeneEintraege()).toEqual([]);
    expect(sessionStorage.length).toBe(sitzungVorher);
    expect(document.cookie).toBe(cookiesVorher);
    service.bandBeantworten(false);
    expect(schreiben).toHaveBeenCalledOnceWith(HOME_HINWEIS_SCHLUESSEL, '1');
    expect(eigeneEintraege()).toEqual([HOME_HINWEIS_SCHLUESSEL]);
  });

  it('kommt nach „Ausblenden“ nicht wieder, auch nicht beim nächsten Besuch', () => {
    willkommenErledigt();
    const service = besuch();
    navigiert('/search');
    service.bandBeantworten(false);
    expect(service.band()).toBeNull();
    const naechster = besuch();
    navigiert('/search');
    expect(naechster.band()).toBeNull();
  });

  it('„Ausblenden“ ist der einzige Knopf: Auch „ja“ startet keinen Rundgang', () => {
    willkommenErledigt();
    const service = besuch();
    navigiert('/search');
    service.bandBeantworten(true);
    expect(service.aktiv()).toBeNull();
    expect(service.band()).toBeNull();
  });

  it('auf anderen Geräten: kein Hinweis', () => {
    ios = false;
    willkommenErledigt();
    const service = besuch();
    navigiert('/search');
    expect(service.band()).toBeNull();
    expect(eigeneEintraege()).toEqual([]);
  });

  it('mit ausgeschaltetem Schalter: kein Hinweis, sein Merker wird nie gelesen', () => {
    schalter = false;
    willkommenErledigt();
    const lesen = spyOn(Storage.prototype, 'getItem').and.callThrough();
    const service = besuch();
    navigiert('/search');
    expect(service.band()).toBeNull();
    expect(lesen).not.toHaveBeenCalledWith(HOME_HINWEIS_SCHLUESSEL);
  });
});
