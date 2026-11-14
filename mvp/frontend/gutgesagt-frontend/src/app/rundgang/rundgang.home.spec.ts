import { DestroyRef } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { NavigationEnd, Router } from '@angular/router';
import { BehaviorSubject, Subject } from 'rxjs';
import { AuthService, UserInfo } from '../auth/auth.service';
import { Art9EinwilligungService } from '../services/art9-einwilligung.service';
import { SearchResponse } from '../services/dtos/searchDtos';
import { StateManagementService } from '../services/state-management.service';
import { HOME_HINWEIS_MERKER } from '../shared/geraetespeicher-schalter';
import { HOME_BILDSCHIRM_MOEGLICH } from './home-bildschirm';
import { RundgangService } from './rundgang.service';
import { HOME_ANGEBOT, WILLKOMMEN } from './rundgang-daten';
import {
  HOME_HINWEIS_SCHLUESSEL,
  MITMACHEN_SCHLUESSEL,
  SCHON_DA_SCHLUESSEL,
  WILLKOMMEN_SCHLUESSEL,
} from './rundgang-merker';

/** Hinweis „Gut gesagt als App“ auf iPhone und iPad im selben Band wie das Willkommen. */
describe('RundgangService: Hinweis Home-Bildschirm', () => {
  const SCHLUESSEL = [WILLKOMMEN_SCHLUESSEL, MITMACHEN_SCHLUESSEL, HOME_HINWEIS_SCHLUESSEL, SCHON_DA_SCHLUESSEL];
  const besucher: UserInfo = { isAuthenticated: false, userId: null, userName: null, claims: null };

  let events: Subject<unknown>;
  let router: { url: string; events: Subject<unknown> };
  let suchStand: StateManagementService;
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
    TestBed.configureTestingModule({
      providers: [
        { provide: Router, useValue: router },
        { provide: AuthService, useValue: { userInfo$: new BehaviorSubject<UserInfo | null>(besucher) } },
        {
          provide: Art9EinwilligungService,
          useValue: { geklaert$: new BehaviorSubject<string | null>(null), geklaert: () => null },
        },
        { provide: HOME_BILDSCHIRM_MOEGLICH, useValue: () => ios },
        { provide: HOME_HINWEIS_MERKER, useFactory: () => schalter },
      ],
    });
    suchStand = TestBed.inject(StateManagementService);
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

  function suche(treffer: number): void {
    suchStand.setSearchResults({
      commentary_search_results: [],
      commentary_search_results_count: treffer,
      generictext_search_results: [],
      generictext_search_results_count: 0,
    } as unknown as SearchResponse);
  }

  /** Willkommen schon beantwortet: Sonst steht es zuerst da. */
  function willkommenErledigt(): void {
    localStorage.setItem(WILLKOMMEN_SCHLUESSEL, '1');
  }

  it('erscheint nicht beim ersten Besuch ohne Suche', () => {
    willkommenErledigt();
    const service = besuch();
    navigiert('/search');
    expect(service.band()).toBeNull();
  });

  it('erscheint beim zweiten Besuch auf der Startseite', () => {
    willkommenErledigt();
    besuch();
    const zweiter = besuch();
    navigiert('/search');
    expect(zweiter.band()).toBe(HOME_ANGEBOT);
  });

  it('erscheint schon beim ersten Besuch nach einer Suche mit Treffern, nicht nach einer ohne', () => {
    willkommenErledigt();
    const service = besuch();
    navigiert('/search');
    suche(0);
    expect(service.band()).toBeNull();
    suche(3);
    expect(service.band()).toBe(HOME_ANGEBOT);
  });

  it('steht nur auf der Startseite, nicht über den Treffern', () => {
    willkommenErledigt();
    besuch();
    const zweiter = besuch();
    navigiert('/result?searchQuery=x');
    expect(zweiter.band()).toBeNull();
  });

  it('nie zusammen mit dem Willkommen und nicht gleich danach im selben Besuch', () => {
    besuch();
    const zweiter = besuch();
    navigiert('/search');
    expect(zweiter.band()).toBe(WILLKOMMEN);
    zweiter.bandBeantworten(false);
    expect(zweiter.band()).toBeNull();
    // Beim nächsten Besuch ist es dran
    const dritter = besuch();
    navigiert('/search');
    expect(dritter.band()).toBe(HOME_ANGEBOT);
  });

  it('kommt nach „Ausblenden“ nicht wieder, auch nicht beim nächsten Besuch', () => {
    willkommenErledigt();
    besuch();
    const zweiter = besuch();
    navigiert('/search');
    zweiter.bandBeantworten(false);
    expect(zweiter.band()).toBeNull();
    expect(localStorage.getItem(HOME_HINWEIS_SCHLUESSEL)).toBe('1');
    const dritter = besuch();
    navigiert('/search');
    expect(dritter.band()).toBeNull();
  });

  it('„Ausblenden“ ist der einzige Knopf: Auch „ja“ startet keinen Rundgang', () => {
    willkommenErledigt();
    besuch();
    const zweiter = besuch();
    navigiert('/search');
    zweiter.bandBeantworten(true);
    expect(zweiter.aktiv()).toBeNull();
    expect(zweiter.band()).toBeNull();
  });

  it('erscheint nicht, wenn der Browser nichts speichern lässt', () => {
    willkommenErledigt();
    spyOn(Storage.prototype, 'setItem').and.throwError('gesperrt');
    const service = besuch();
    navigiert('/search');
    suche(3);
    expect(service.band()).toBeNull();
  });

  it('erscheint nicht, wenn der Speicher ganz fehlt (privates Fenster, gesperrt)', () => {
    spyOn(Storage.prototype, 'getItem').and.throwError('gesperrt');
    spyOn(Storage.prototype, 'setItem').and.throwError('gesperrt');
    const service = besuch();
    navigiert('/search');
    // Ohne Speicher steht das Willkommen da; ausgeblendet folgt kein Hinweis
    expect(service.band()).toBe(WILLKOMMEN);
    service.bandBeantworten(false);
    const zweiter = besuch();
    navigiert('/search');
    suche(3);
    expect(service.band()).toBeNull();
    expect(zweiter.band()).not.toBe(HOME_ANGEBOT);
  });

  it('auf anderen Geräten: kein Hinweis und kein Merker', () => {
    ios = false;
    willkommenErledigt();
    besuch();
    const zweiter = besuch();
    navigiert('/search');
    suche(3);
    expect(zweiter.band()).toBeNull();
    expect(localStorage.getItem(SCHON_DA_SCHLUESSEL)).toBeNull();
  });

  it('mit ausgeschaltetem Schalter: kein Hinweis und kein Merker', () => {
    schalter = false;
    willkommenErledigt();
    besuch();
    const zweiter = besuch();
    navigiert('/search');
    suche(3);
    expect(zweiter.band()).toBeNull();
    expect(localStorage.getItem(SCHON_DA_SCHLUESSEL)).toBeNull();
  });
});
