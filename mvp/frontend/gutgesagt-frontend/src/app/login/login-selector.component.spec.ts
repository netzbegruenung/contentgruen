import { ComponentFixture, TestBed } from '@angular/core/testing';
import { LoginSelectorComponent, WARTELISTE_TEXT } from './login-selector.component';
import { EINLADUNG_AB } from '../shared/einladung-ab';
import { ORGANISATION } from '../shared/organisation';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { Router, ActivatedRoute } from '@angular/router';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { of } from 'rxjs';
import { MatDialog, MatDialogRef } from '@angular/material/dialog';
import { FeedbackDialogComponent } from '../shared/feedback/feedback-dialog.component';

describe('LoginSelectorComponent', () => {
  let component: LoginSelectorComponent;
  let fixture: ComponentFixture<LoginSelectorComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        LoginSelectorComponent,
        HttpClientTestingModule,
        BrowserAnimationsModule
      ],
      providers: [
        { provide: Router, useValue: {
          navigate: jasmine.createSpy('navigate'),
          navigateByUrl: jasmine.createSpy('navigateByUrl'),
          url: '/login'
        } },
        { provide: ActivatedRoute, useValue: {
          snapshot: {
            queryParams: {}
          },
          params: of({}),
          queryParams: of({})
        } }
      ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(LoginSelectorComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  // Designrunde 17.11.: Anmeldung oben, darunter immer sichtbar, wie man zu einem Konto kommt
  describe('Noch kein Konto?', () => {
    it('nennt die Mitgliedschaft mit Link zum Mitgliedsantrag, auch waehrend die Anmeldewege laden', () => {
      const weg = fixture.nativeElement.querySelector('.konto-weg') as HTMLElement;

      expect(weg.querySelector('h2')?.textContent?.trim()).toBe('Noch kein Konto?');
      expect(weg.querySelector('a')?.getAttribute('href')).toBe(ORGANISATION.mitgliedsantragUrl);
      expect(weg.querySelector('a')?.textContent?.trim()).toBe(`Mitglied der ${ORGANISATION.name}`);
    });

    it('zeigt die Einladung bis zur Realm-Umstellung nur als eingeklappte Vorschau ohne Funktion', () => {
      const vorschau = fixture.nativeElement.querySelector('details.einladung-vorschau') as HTMLDetailsElement;

      expect(vorschau.open).toBeFalse();
      expect(vorschau.querySelector('summary')?.textContent).toContain(`Ab ${EINLADUNG_AB}`);
      expect((vorschau.querySelector('.einladung-knopf') as HTMLButtonElement).disabled).toBeTrue();
      expect(vorschau.querySelector('a[href="/einladung"]')).toBeNull();
    });

    it('oeffnet fuer die Warteliste den Feedback-Dialog mit vorbelegtem Text', () => {
      const dialog = fixture.debugElement.injector.get(MatDialog);
      const offen = spyOn(dialog, 'open').and.returnValue({} as MatDialogRef<unknown>);

      (fixture.nativeElement.querySelector('.warteliste-knopf') as HTMLButtonElement).click();

      expect(offen).toHaveBeenCalledWith(
        FeedbackDialogComponent,
        jasmine.objectContaining({ data: { text: WARTELISTE_TEXT } }),
      );
    });
  });

  describe('Grund und nur eingeschaltete Anmeldewege (#600)', () => {
    let http: HttpTestingController;

    function modes(keycloakEnabled: boolean, managedAuthEnabled: boolean): HTMLElement {
      http = TestBed.inject(HttpTestingController);
      http.expectOne(r => r.url.endsWith('/api/auth/modes')).flush({ keycloakEnabled, managedAuthEnabled });
      fixture.detectChanges();
      return fixture.nativeElement;
    }

    it('blendet die ausgeschaltete Direktanmeldung aus statt sie auszugrauen (Test, Produktion)', () => {
      const el = modes(true, false);

      expect(el.querySelector('.keycloak-button')).not.toBeNull();
      expect(el.querySelector('.gutgesagt-button')).toBeNull();
      expect(el.querySelector('.divider-container')).toBeNull();
      expect(el.querySelector('.disabled-notice')).toBeNull();
      expect(el.querySelector('.login-options button[disabled]')).toBeNull();
    });

    it('blendet den ausgeschalteten Netzbegrünung-Login aus (Dev-Stack)', () => {
      const el = modes(false, true);

      expect(el.querySelector('.keycloak-button')).toBeNull();
      expect(el.querySelector('.gutgesagt-button')).not.toBeNull();
      expect(el.querySelector('.divider-container')).toBeNull();
    });

    it('zeigt beide Wege mit "oder", wenn beide an sind', () => {
      const el = modes(true, true);

      expect(el.querySelector('.keycloak-button')).not.toBeNull();
      expect(el.querySelector('.gutgesagt-button')).not.toBeNull();
      expect(el.querySelector('.divider-container')).not.toBeNull();
    });

    it('sagt, dass Anmelden nicht geht, wenn kein Weg an ist', () => {
      const el = modes(false, false);

      expect(el.querySelector('.disabled-notice')?.textContent).toContain('Anmelden ist gerade nicht möglich');
    });

    it('zeigt beide Wege, wenn die Modi nicht zu laden sind, statt einen toten Weg', () => {
      http = TestBed.inject(HttpTestingController);
      http.expectOne(r => r.url.endsWith('/api/auth/modes')).flush('x', { status: 500, statusText: 'err' });
      fixture.detectChanges();
      const el: HTMLElement = fixture.nativeElement;

      expect(el.querySelector('.keycloak-button')).not.toBeNull();
      expect(el.querySelector('.gutgesagt-button')).not.toBeNull();
    });

    it('nennt den Netzbegrünung-Login ohne Keycloak und SSO', () => {
      const el = modes(true, false);
      const text = el.textContent ?? '';

      expect(el.querySelector('.keycloak-button')?.textContent).toContain('Mit Netzbegrünung-Konto anmelden');
      expect(text).not.toMatch(/Keycloak|SSO|Selbstregistrierung|Beta-Account/);
      expect(text).toContain('Noch kein Konto?');
    });

    it('zeigt ohne Ziel aus "Antworten" keinen Grund', () => {
      const el = modes(true, false);

      expect(el.querySelector('.anmeldegrund')).toBeNull();
    });
  });
});

describe('LoginSelectorComponent nach "Antworten" (#600)', () => {
  afterEach(() => sessionStorage.removeItem('loginReturnUrl'));

  it('sagt oben, wozu die Anmeldung nötig ist', async () => {
    await TestBed.configureTestingModule({
      imports: [LoginSelectorComponent, HttpClientTestingModule, BrowserAnimationsModule],
      providers: [
        { provide: Router, useValue: { navigate: jasmine.createSpy('navigate'), url: '/login' } },
        { provide: ActivatedRoute, useValue: {
          snapshot: { queryParams: { returnUrl: '/workflow/add-commentary?aussage=f6efb534-ee3a-4969-b8b8-2f1f9b9bb95d' } },
          params: of({}),
          queryParams: of({})
        } }
      ]
    }).compileComponents();

    const fixture = TestBed.createComponent(LoginSelectorComponent);
    fixture.detectChanges();

    const grund: HTMLElement | null = fixture.nativeElement.querySelector('.anmeldegrund');
    expect(grund?.textContent?.trim()).toBe('Zum Beantworten melde dich an.');
    // Der Grund steht ueber den Anmeldewegen und dem Hinweis zum Konto
    expect(fixture.nativeElement.querySelector('.component-box').firstElementChild).toBe(grund);
  });
});
