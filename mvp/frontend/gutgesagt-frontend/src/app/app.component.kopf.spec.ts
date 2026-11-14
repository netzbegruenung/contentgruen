import { TestBed, ComponentFixture } from '@angular/core/testing';
import { BreakpointObserver } from '@angular/cdk/layout';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideAnimations } from '@angular/platform-browser/animations';
import { ActivatedRoute, Router, RouterLinkActive } from '@angular/router';
import { By } from '@angular/platform-browser';
import { MatDialog } from '@angular/material/dialog';
import { BehaviorSubject, of, throwError } from 'rxjs';
import { AppComponent } from './app.component';
import { AuthService, UserInfo } from './auth/auth.service';
import { NavigationService } from './services/navigation.service';
import { FarbschemaService } from './services/farbschema.service';
import { FeedbackDialogComponent } from './shared/feedback/feedback-dialog.component';
import {
  ALTE_PROFILBILD_SCHLUESSEL,
  ANONYMES_PROFILBILD,
  PROFILBILD_SCHLUESSEL,
  ProfilbildService,
} from './services/profilbild.service';
import { ProfilbildDialogComponent } from './shared/profilbild/profilbild-dialog.component';
import { RUECKKEHRZIEL_SCHLUESSEL } from './login/rueckkehrziel';
import { RundgangService } from './rundgang/rundgang.service';
import { MatTooltip } from '@angular/material/tooltip';
import { ZuTunService } from './services/zu-tun.service';
import { ModerationService } from './services/moderation.service';

/**
 * Der Desktop-Kopf aus den Befunden der Testsessions (#343): ein Weg zum Anmelden,
 * der Avatar wuerfelt nicht, sondern oeffnet angemeldet ein Profilmenue (Meine
 * Beitraege, Abmelden), und der Knopf "Feedback" ist fuer alle erreichbar.
 */
describe('AppComponent - Desktop-Kopf', () => {
  let fixture: ComponentFixture<AppComponent>;
  let router: jasmine.SpyObj<Router>;
  let navigation: jasmine.SpyObj<NavigationService>;
  let dialog: jasmine.SpyObj<MatDialog>;
  let userInfo$: BehaviorSubject<UserInfo | null>;

  const ANGEMELDET: UserInfo = {
    isAuthenticated: true,
    userId: 'user-001',
    userName: 'Test User',
    claims: {},
  };
  const BESUCHER: UserInfo = { isAuthenticated: false, userId: null, userName: null, claims: null };

  function starten(person: UserInfo) {
    const auth = TestBed.inject(AuthService) as jasmine.SpyObj<AuthService>;
    auth.fetchUserInfo.and.returnValue(
      person.isAuthenticated ? of(person) : throwError(() => new Error('401'))
    );
    auth.setUserInfo.and.callFake((u: UserInfo) => userInfo$.next(u));
    userInfo$.next(person);
    fixture = TestBed.createComponent(AppComponent);
    fixture.detectChanges();
  }

  function kopf(): HTMLElement {
    return fixture.nativeElement.querySelector('.header') as HTMLElement;
  }

  function avatar(): HTMLElement {
    return kopf().querySelector('.avatar-container') as HTMLElement;
  }

  beforeEach(async () => {
    userInfo$ = new BehaviorSubject<UserInfo | null>(null);
    router = jasmine.createSpyObj('Router', ['navigate', 'navigateByUrl', 'createUrlTree', 'serializeUrl'], {
      events: of({}),
      url: '/search',
    });
    navigation = jasmine.createSpyObj('NavigationService', [
      'navigateToMeineBeitraege',
      'navigateToContribute',
      'navigateToEinwerfen',
      'navigateToFangkorb',
      'navigateHome',
      'goBack',
    ]);
    dialog = jasmine.createSpyObj('MatDialog', ['open']);

    await TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideAnimations(),
        {
          provide: AuthService,
          useValue: jasmine.createSpyObj('AuthService', ['fetchUserInfo', 'setUserInfo', 'logout', 'getCurrentUserId'], {
            userInfo$: userInfo$.asObservable(),
          }),
        },
        { provide: NavigationService, useValue: navigation },
        { provide: Router, useValue: router },
        { provide: ActivatedRoute, useValue: { params: of({}), queryParams: of({}), snapshot: {} } },
        // Desktop, unabhaengig von der Fenstergroesse des Testbrowsers.
        { provide: BreakpointObserver, useValue: { observe: () => of({ matches: false, breakpoints: {} }) } },
      ],
    })
      // MatDialog sitzt im Standalone-Import von AppComponent; der Override ersetzt ihn dort.
      .overrideProvider(MatDialog, { useValue: dialog })
      .compileComponents();
  });

  describe('Besucher', () => {
    beforeEach(() => starten(BESUCHER));

    it('hat genau einen Weg zum Anmelden: den Knopf, und keinen Avatar (#599)', () => {
      const anmelden = Array.from(kopf().querySelectorAll('button, [role="button"]')).filter(
        (e) => e.textContent?.includes('Anmelden') || e.getAttribute('aria-label') === 'Anmelden'
      );
      expect(anmelden.length).toBe(1);
      expect(anmelden[0].tagName).toBe('BUTTON');

      expect(avatar()).toBeNull();
      expect(kopf().textContent).not.toContain('Nicht angemeldet');
    });

    it('meldet nur ueber einen Klick im Kopf an, egal wie das Element beschriftet ist', () => {
      const komponente = fixture.componentInstance;
      const anmelden = spyOn(komponente, 'login');
      const anmeldenMitZiel = spyOn(komponente, 'loginWithReturnUrl');
      // Der Umschalter hell/dunkel setzt das Attribut am Testdokument und den localStorage
      spyOn(TestBed.inject(FarbschemaService), 'umschalten');

      const klickbar = kopf().querySelectorAll('button, a, [role="button"], [tabindex], .avatar-container, img');
      klickbar.forEach((e) => (e as HTMLElement).click());

      expect(anmelden.calls.count() + anmeldenMitZiel.calls.count()).toBe(1);
    });

    // #620: Das Logo ist der Weg zur Startseite, "Start" im Kopf entfaellt
    it('fuehrt mit dem Logo "Startseite" zur Startseite; die Ueberschrift nennt nur die Seite', () => {
      const link = kopf().querySelector('a.logo-link') as HTMLAnchorElement;
      expect(link.getAttribute('aria-label')).toBe('Startseite');
      expect(link.querySelector('img')!.getAttribute('alt')).toBe('');
      expect(kopf().querySelector('h1 a')).toBeNull();
      expect(kopf().querySelector('[data-testid="start-knopf"]')).toBeNull();

      link.click();

      expect(navigation.navigateHome).toHaveBeenCalledTimes(1);
    });

    it('sieht den Knopf Feedback und oeffnet damit das Formular', () => {
      const knopf = kopf().querySelector('[data-testid="feedback-knopf"]') as HTMLElement;
      expect(knopf.textContent).toContain('Feedback');

      knopf.click();

      expect(dialog.open).toHaveBeenCalledWith(FeedbackDialogComponent, jasmine.anything());
    });
  });

  describe('auf der Anmeldeseite (#645)', () => {
    function aufSeite(url: string) {
      (Object.getOwnPropertyDescriptor(router, 'url')!.get as jasmine.Spy).and.returnValue(url);
      starten(BESUCHER);
    }

    function anmeldenKnopf(): Element | undefined {
      return Array.from(kopf().querySelectorAll('button')).find((e) => e.textContent?.trim() === 'Anmelden');
    }

    it('blendet den Kopfknopf "Anmelden" auf /login und /login/managed aus', () => {
      aufSeite('/login/managed?returnUrl=%2Fcontribute');
      expect(anmeldenKnopf()).toBeUndefined();
      expect(kopf().querySelector('h1')!.textContent!.trim()).toBe('Anmelden');
    });

    it('zeigt ihn auf anderen Seiten weiter', () => {
      aufSeite('/hier-fehlt-eine-antwort');
      expect(anmeldenKnopf()).toBeDefined();
    });
  });

  describe('Angemeldet', () => {
    beforeEach(() => starten(ANGEMELDET));

    it('markiert den Kopf-Link "Hier fehlt eine Antwort" auf seiner Seite mit aria-current (#645)', () => {
      const link = fixture.debugElement
        .queryAll(By.css('a.header-link'))
        .find((e) => (e.nativeElement as HTMLElement).textContent?.includes('Hier fehlt eine Antwort'))!;
      const aktiv = link.injector.get(RouterLinkActive);

      expect(aktiv.ariaCurrentWhenActive).toBe('page');
    });

    function profilmenue(): HTMLElement[] {
      return Array.from(document.querySelectorAll('.profilmenue-eintrag')) as HTMLElement[];
    }

    function eintrag(text: string): HTMLElement {
      return profilmenue().find((e) => e.textContent?.includes(text))!;
    }

    async function menueOeffnen(): Promise<void> {
      avatar().click();
      fixture.detectChanges();
      await fixture.whenStable();
    }

    it('Klick auf den Avatar oeffnet das Profilmenue und wuerfelt kein neues Bild', async () => {
      const vorher = fixture.componentInstance.selectedProfilePictureUrl;

      expect(avatar().tagName).toBe('BUTTON');
      expect(avatar().getAttribute('aria-label')).toBe('Profilmenü öffnen');
      expect(avatar().getAttribute('aria-haspopup')).toBe('menu');

      avatar().click();
      fixture.detectChanges();
      await fixture.whenStable();

      expect(profilmenue().map((e) => e.textContent?.trim())).toEqual([
        jasmine.stringContaining('Schnell einwerfen'),
        jasmine.stringContaining('Fangkorb'),
        jasmine.stringContaining('Meine Beiträge'),
        jasmine.stringContaining('Profilbild wählen'),
        jasmine.stringContaining('Datenschutz-Einstellungen'),
        jasmine.stringContaining('Abmelden'),
      ]);
      expect(navigation.navigateToMeineBeitraege).not.toHaveBeenCalled();
      expect(fixture.componentInstance.selectedProfilePictureUrl).toBe(vorher);
      expect(sessionStorage.getItem('profilePicture')).toBeNull();
    });

    it('oeffnet das Profilmenue mit der Tastatur und fuehrt zu Meine Beitraege', async () => {
      avatar().focus();
      avatar().dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
      avatar().click(); // Enter auf einem <button> loest im Browser den Klick aus
      fixture.detectChanges();
      await fixture.whenStable();

      expect(document.activeElement).toBe(profilmenue()[0]);
      eintrag('Meine Beiträge').click();

      expect(navigation.navigateToMeineBeitraege).toHaveBeenCalledTimes(1);
    });

    // #620: statt zweier unbeschrifteter Symbole im Kopf
    it('fuehrt ueber das Profilmenue zu Schnell einwerfen und in den Fangkorb', async () => {
      await menueOeffnen();
      eintrag('Schnell einwerfen').click();
      expect(navigation.navigateToEinwerfen).toHaveBeenCalledTimes(1);

      await menueOeffnen();
      eintrag('Fangkorb').click();
      expect(navigation.navigateToFangkorb).toHaveBeenCalledTimes(1);
    });

    it('meldet ueber das Profilmenue ab', async () => {
      const auth = TestBed.inject(AuthService) as jasmine.SpyObj<AuthService>;
      avatar().click();
      fixture.detectChanges();
      await fixture.whenStable();

      eintrag('Abmelden').click();

      expect(auth.logout).toHaveBeenCalledTimes(1);
    });

    it('fuehrt ueber das Profilmenue zur Art.-9-Einwilligung (#489)', async () => {
      avatar().click();
      fixture.detectChanges();
      await fixture.whenStable();

      eintrag('Datenschutz-Einstellungen').click();

      expect(router.navigate).toHaveBeenCalledWith(['/einwilligung']);
    });

    it('oeffnet ueber das Profilmenue den Dialog Profilbild waehlen', async () => {
      avatar().click();
      fixture.detectChanges();
      await fixture.whenStable();

      eintrag('Profilbild wählen').click();

      expect(dialog.open).toHaveBeenCalledWith(ProfilbildDialogComponent, jasmine.anything());
    });

    it('zeigt das gewaehlte Profilbild sofort im Kopf', () => {
      const service = TestBed.inject(ProfilbildService);
      const option = service.auswahl[4];

      service.waehlen(option.id);
      fixture.detectChanges();

      expect(avatar().querySelector('img')?.getAttribute('src')).toBe(option.url);
      expect(avatar().querySelector('img')?.getAttribute('alt')).toBe('Profilbild');
      localStorage.removeItem(PROFILBILD_SCHLUESSEL);
    });

    it('hat im Kopf keinen eigenen Link Meine Beitraege mehr neben dem Avatar', () => {
      const links = Array.from(kopf().querySelectorAll('button, [role="button"]')).filter(
        (e) => e.textContent?.includes('Meine Beiträge') || e.getAttribute('aria-label') === 'Meine Beiträge anzeigen'
      );
      expect(links.length).toBe(0);
    });

    // Design-Audit A1/B4 (#512): Abmelden nur im Profilmenue.
    it('hat Abmelden nur im Profilmenue, nicht als eigenen Link im Kopf', () => {
      const abmelden = Array.from(kopf().querySelectorAll('button, a, [role="button"]')).filter((e) =>
        e.textContent?.includes('Abmelden')
      );
      expect(abmelden.length).toBe(0);
    });

    // #620: Der Kopf hatte angemeldet acht Elemente, zwei davon unbeschriftete Symbole
    it('hat keine unbeschrifteten Symbol-Knoepfe fuer Fangkorb und Einwerfen mehr', () => {
      expect(kopf().querySelector('[data-testid="fangkorb-knopf"]')).toBeNull();
      expect(kopf().querySelector('[aria-label="Schnell einwerfen"]')).toBeNull();
      expect(kopf().querySelectorAll('button[mat-icon-button]:not(.back-button-header)').length).toBe(0);
    });

    // #599: drei runde Symbole ohne Beschriftung waren nicht zu deuten
    it('beschriftet Feedback und Hilfe als Textlinks mit Symbol fuer schmale Kopfzeilen, ohne "Start" (#620)', () => {
      const textlinks = Array.from(kopf().querySelectorAll('button.header-link'));
      expect(textlinks.map((k) => k.querySelector('.kopf-text')!.textContent!.trim())).toEqual(['Feedback', 'Hilfe']);
      expect(kopf().querySelector('[data-testid="start-knopf"]')).toBeNull();
      for (const k of textlinks) {
        expect(k.querySelector('mat-icon')!.getAttribute('aria-hidden')).toBe('true');
      }
    });

    it('setzt lange Titel kleiner und laesst die Begruessung weichen, kurze nicht', () => {
      const komponente = fixture.componentInstance;
      komponente.pageTitle = 'Hintergrundinfo verfassen';
      fixture.detectChanges();
      expect(kopf().classList).toContain('header--titel-lang');
      expect(kopf().querySelector('.desktop-header-title')!.classList).toContain('desktop-header-title--lang');

      komponente.pageTitle = 'Fangkorb';
      fixture.detectChanges();
      expect(kopf().classList).not.toContain('header--titel-lang');
    });

    it('behaelt fuer Screenreader den Namen der Textlinks, auch wenn sie als Icon erscheinen', () => {
      const link = Array.from(kopf().querySelectorAll('a.header-link')).find((a) =>
        a.textContent!.includes('Hier fehlt eine Antwort'),
      )!;
      expect(link.querySelector('.kopf-text')!.textContent!.trim()).toBe('Hier fehlt eine Antwort');
      expect(link.querySelector('mat-icon')!.getAttribute('aria-hidden')).toBe('true');
    });

    it('sieht den Knopf Feedback ebenfalls', () => {
      (kopf().querySelector('[data-testid="feedback-knopf"]') as HTMLElement).click();

      expect(dialog.open).toHaveBeenCalledWith(FeedbackDialogComponent, jasmine.anything());
    });
  });

  // R55 (#644): Nach 4x Tab stand der Fokus auf "Hilfe", nicht im Suchfeld
  describe('Skip-Link "Zur Suche"', () => {
    beforeEach(() => starten(BESUCHER));

    it('steht auf dem Start als erstes fokussierbares Element', () => {
      const erstes = fixture.nativeElement.querySelector('a[href], button') as HTMLElement;
      expect(erstes.textContent!.trim()).toBe('Zur Suche');
      expect(erstes.getAttribute('href')).toBe('#suche');
    });

    it('setzt den Fokus ins Suchfeld, ohne die Adresse zu aendern', () => {
      const feld = document.createElement('input');
      feld.id = 'suche';
      document.body.appendChild(feld);
      try {
        const link = fixture.nativeElement.querySelector('[data-testid="skip-link"]') as HTMLAnchorElement;
        const klick = new MouseEvent('click', { cancelable: true, bubbles: true });
        link.dispatchEvent(klick);

        expect(document.activeElement).toBe(feld);
        expect(klick.defaultPrevented).toBeTrue();
      } finally {
        feld.remove();
      }
    });
  });

  // R59 (#644): Der gelbe Punkt an "Beitragen" stand ohne Erklaerung da
  describe('Neu-Punkt an Beitragen', () => {
    beforeEach(() => starten(ANGEMELDET));

    it('erklaert den Punkt per Tooltip und fuer Screenreader', () => {
      (TestBed.inject(RundgangService) as any).mitmachenOffen.set(true);
      fixture.detectChanges();
      const knopf = fixture.nativeElement.querySelector('.beitragen-knopf') as HTMLElement;

      expect(knopf.querySelector('.neu-punkt')).not.toBeNull();
      const tooltip = fixture.debugElement.query(By.css('.beitragen-knopf')).injector.get(MatTooltip);
      expect(tooltip.message).toBe('Neu: so geht Beitragen');
      expect(tooltip.disabled).toBeFalse();
    });
  });

  describe('Profilbild ohne Wahl nicht im Browser gespeichert (#437)', () => {
    function gespeichert(): string[][] {
      return [Object.keys(localStorage), Object.keys(sessionStorage)];
    }

    afterEach(() => ALTE_PROFILBILD_SCHLUESSEL.forEach((s: string) => sessionStorage.removeItem(s)));

    it('zeigt Besuchern das anonyme Profilbild und legt nichts im Browser ab', () => {
      const vorher = gespeichert();
      starten(BESUCHER);

      expect(fixture.componentInstance.selectedProfilePictureUrl).toBe(ANONYMES_PROFILBILD);
      expect(gespeichert()).toEqual(vorher);
    });

    it('zeigt Mitwirkenden ein festes Profilbild und legt nichts im Browser ab', () => {
      const vorher = gespeichert();
      starten(ANGEMELDET);

      const urls = TestBed.inject(ProfilbildService).auswahl.map((o) => o.url);
      expect(urls).toContain(fixture.componentInstance.selectedProfilePictureUrl);
      expect(gespeichert()).toEqual(vorher);
    });

    it('raeumt die Eintraege frueherer Versionen beim Start weg', () => {
      sessionStorage.setItem('profilePicture', '/avatars/female1.svg');
      sessionStorage.setItem('anonymousAvatar', '/avatars/anon-question.svg');
      sessionStorage.setItem('userAvatar', '/avatars/male2.svg');

      starten(BESUCHER);

      ALTE_PROFILBILD_SCHLUESSEL.forEach((s: string) => expect(sessionStorage.getItem(s)).toBeNull());
    });
  });

  describe('Rueckkehrziel nach dem Anmelden (Befund 10 aus dem Review zu PR 458)', () => {
    afterEach(() => sessionStorage.removeItem(RUECKKEHRZIEL_SCHLUESSEL));

    it('fuehrt angemeldet zum gemerkten Ziel und loescht es', () => {
      sessionStorage.setItem(RUECKKEHRZIEL_SCHLUESSEL, '/contribute');

      starten(ANGEMELDET);

      expect(router.navigateByUrl).toHaveBeenCalledWith('/contribute');
      expect(sessionStorage.getItem(RUECKKEHRZIEL_SCHLUESSEL)).toBeNull();
    });

    it('startet auch, wenn der Browser den sessionStorage sperrt', () => {
      const spione = [
        spyOn(Storage.prototype, 'getItem').and.throwError('SecurityError'),
        spyOn(Storage.prototype, 'removeItem').and.throwError('SecurityError'),
      ];

      expect(() => starten(ANGEMELDET)).not.toThrow();
      expect(router.navigateByUrl).not.toHaveBeenCalled();
      spione.forEach((spion) => spion.and.callThrough());
    });
  });
  // Nutzerfuehrung 13.11.2026: offene Meldungen sieht man schon im Kopf.
  describe('Admin', () => {
    it('fragt fuer Nicht-Admins nie nach offenen Meldungen', () => {
      const moderation = jasmine.createSpyObj('ModerationService', ['getReports', 'getLoeschauftraege']);
      TestBed.overrideProvider(ModerationService, { useValue: moderation });
      starten(ANGEMELDET);

      expect(kopf().querySelector('app-offene-meldungen-zahl')).toBeNull();
      expect(moderation.getReports).not.toHaveBeenCalled();
    });

    it('zeigt am Admin-Link die Zahl offener Meldungen', () => {
      TestBed.overrideProvider(ZuTunService, {
        useValue: { meldungen$: of({ daten: { anzahl: 3, mehr: false, aelteste: null }, fehler: false }) },
      });
      starten({ ...ANGEMELDET, isAdmin: true });

      const admin = (Array.from(kopf().querySelectorAll('a.header-link')) as HTMLElement[]).find((a) =>
        a.textContent?.includes('Admin'),
      )!;
      expect(admin.querySelector('.zahl')!.textContent!.trim()).toBe('3');
      expect(admin.textContent).toContain('3 offene Meldungen');
    });
  });
});
