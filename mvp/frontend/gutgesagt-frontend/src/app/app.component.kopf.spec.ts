import { TestBed, ComponentFixture } from '@angular/core/testing';
import { BreakpointObserver } from '@angular/cdk/layout';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideAnimations } from '@angular/platform-browser/animations';
import { ActivatedRoute, Router } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { BehaviorSubject, of, throwError } from 'rxjs';
import { AppComponent } from './app.component';
import { AuthService, UserInfo } from './auth/auth.service';
import { NavigationService } from './services/navigation.service';
import { FeedbackDialogComponent } from './shared/feedback/feedback-dialog.component';
import { ALTE_PROFILBILD_SCHLUESSEL, ANONYMER_AVATAR, PROFILBILDER } from './services/profilbild.service';

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
      'navigateToContributions',
      'navigateToContribute',
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
          useValue: jasmine.createSpyObj('AuthService', ['fetchUserInfo', 'setUserInfo', 'logout'], {
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

    it('hat genau einen Weg zum Anmelden: den Knopf, nicht den Avatar', () => {
      const anmelden = Array.from(kopf().querySelectorAll('button, [role="button"]')).filter(
        (e) => e.textContent?.includes('Anmelden') || e.getAttribute('aria-label') === 'Anmelden'
      );
      expect(anmelden.length).toBe(1);
      expect(anmelden[0].tagName).toBe('BUTTON');

      expect(avatar().getAttribute('role')).toBeNull();
      expect(avatar().getAttribute('tabindex')).toBeNull();
      avatar().click();
      expect(router.navigate).not.toHaveBeenCalled();
    });

    it('meldet nur ueber einen Klick im Kopf an, egal wie das Element beschriftet ist', () => {
      const komponente = fixture.componentInstance;
      const anmelden = spyOn(komponente, 'login');
      const anmeldenMitZiel = spyOn(komponente, 'loginWithReturnUrl');

      const klickbar = kopf().querySelectorAll('button, a, [role="button"], [tabindex], .avatar-container, img');
      klickbar.forEach((e) => (e as HTMLElement).click());

      expect(anmelden.calls.count() + anmeldenMitZiel.calls.count()).toBe(1);
    });

    it('sieht den Knopf Feedback und oeffnet damit das Formular', () => {
      const knopf = kopf().querySelector('[data-testid="feedback-knopf"]') as HTMLElement;
      expect(knopf.textContent).toContain('Feedback');

      knopf.click();

      expect(dialog.open).toHaveBeenCalledWith(FeedbackDialogComponent, jasmine.anything());
    });
  });

  describe('Angemeldet', () => {
    beforeEach(() => starten(ANGEMELDET));

    function profilmenue(): HTMLElement[] {
      return Array.from(document.querySelectorAll('.profilmenue-eintrag')) as HTMLElement[];
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
        jasmine.stringContaining('Meine Beiträge'),
        jasmine.stringContaining('Abmelden'),
      ]);
      expect(navigation.navigateToContributions).not.toHaveBeenCalled();
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
      profilmenue()[0].click();

      expect(navigation.navigateToContributions).toHaveBeenCalledTimes(1);
    });

    it('meldet ueber das Profilmenue ab', async () => {
      const auth = TestBed.inject(AuthService) as jasmine.SpyObj<AuthService>;
      avatar().click();
      fixture.detectChanges();
      await fixture.whenStable();

      profilmenue()[1].click();

      expect(auth.logout).toHaveBeenCalledTimes(1);
    });

    it('hat im Kopf keinen eigenen Link Meine Beitraege mehr neben dem Avatar', () => {
      const links = Array.from(kopf().querySelectorAll('button, [role="button"]')).filter(
        (e) => e.textContent?.includes('Meine Beiträge') || e.getAttribute('aria-label') === 'Meine Beiträge anzeigen'
      );
      expect(links.length).toBe(0);
    });

    it('sieht den Knopf Feedback ebenfalls', () => {
      (kopf().querySelector('[data-testid="feedback-knopf"]') as HTMLElement).click();

      expect(dialog.open).toHaveBeenCalledWith(FeedbackDialogComponent, jasmine.anything());
    });
  });
  describe('Profilbild nur im Speicher der Seite (#437)', () => {
    afterEach(() => ALTE_PROFILBILD_SCHLUESSEL.forEach((s) => sessionStorage.removeItem(s)));

    it('zeigt Besuchern den anonymen Avatar und legt nichts im sessionStorage ab', () => {
      const vorher = Object.keys(sessionStorage);
      starten(BESUCHER);

      expect(fixture.componentInstance.selectedProfilePictureUrl).toBe(ANONYMER_AVATAR);
      expect(Object.keys(sessionStorage)).toEqual(vorher);
    });

    it('zeigt Mitwirkenden ein Profilbild und legt nichts im sessionStorage ab', () => {
      const vorher = Object.keys(sessionStorage);
      starten(ANGEMELDET);

      expect(PROFILBILDER).toContain(fixture.componentInstance.selectedProfilePictureUrl);
      expect(Object.keys(sessionStorage)).toEqual(vorher);
    });

    it('raeumt die Eintraege frueherer Versionen beim Start weg', () => {
      sessionStorage.setItem('profilePicture', '/avatars/female1.svg');
      sessionStorage.setItem('anonymousAvatar', '/avatars/anon-question.svg');
      sessionStorage.setItem('userAvatar', '/avatars/male2.svg');

      starten(BESUCHER);

      ALTE_PROFILBILD_SCHLUESSEL.forEach((s) => expect(sessionStorage.getItem(s)).toBeNull());
    });
  });
});
