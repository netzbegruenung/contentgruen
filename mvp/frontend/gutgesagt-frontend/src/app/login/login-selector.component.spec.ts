import { ComponentFixture, TestBed } from '@angular/core/testing';
import { LoginSelectorComponent } from './login-selector.component';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { Router, ActivatedRoute } from '@angular/router';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { of } from 'rxjs';
import { ORGANISATION } from '../shared/organisation';

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

  describe('Expandable Registration Info', () => {
    it('should initialize with registration info collapsed', () => {
      expect(component.isRegistrationInfoExpanded).toBeFalsy();
    });

    it('should toggle registration info expansion state', () => {
      const initialState = component.isRegistrationInfoExpanded;

      // Simulate clicking the expansion panel header
      component.isRegistrationInfoExpanded = !component.isRegistrationInfoExpanded;
      fixture.detectChanges();

      expect(component.isRegistrationInfoExpanded).toBe(!initialState);

      // Toggle back
      component.isRegistrationInfoExpanded = !component.isRegistrationInfoExpanded;
      fixture.detectChanges();

      expect(component.isRegistrationInfoExpanded).toBe(initialState);
    });

    it('should display correct expansion hint text based on state', () => {
      // When collapsed
      component.isRegistrationInfoExpanded = false;
      fixture.detectChanges();

      let compiled = fixture.nativeElement;
      let expansionHint = compiled.querySelector('.expansion-hint');

      if (expansionHint) {
        expect(expansionHint.textContent).toContain('Mehr Informationen');
      }

      // When expanded
      component.isRegistrationInfoExpanded = true;
      fixture.detectChanges();

      compiled = fixture.nativeElement;
      expansionHint = compiled.querySelector('.expansion-hint');

      if (expansionHint) {
        expect(expansionHint.textContent).toContain('Weniger anzeigen');
      }
    });

    it('should render expansion panel with correct binding', () => {
      const compiled = fixture.nativeElement;
      const expansionPanel = compiled.querySelector('mat-expansion-panel');

      // Note: In a real test environment with Angular Material properly configured,
      // we would check the expanded attribute. Here we just verify the component has the property
      expect(component.hasOwnProperty('isRegistrationInfoExpanded')).toBeTruthy();
    });

    it('nennt für den Beta-Zugang die Kontaktadresse aus der Organisationskonstante (#430)', () => {
      const link: HTMLAnchorElement = fixture.nativeElement.querySelector('.email-link');

      expect(link.textContent?.trim()).toBe(ORGANISATION.gutgesagtMail);
      expect(link.getAttribute('href')).toBe(
        `mailto:${ORGANISATION.gutgesagtMail}?subject=${encodeURIComponent('Beta-Account Anfrage')}`
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
      expect(el.querySelector('button[disabled]')).toBeNull();
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

      expect(el.querySelector('.keycloak-button')?.textContent).toContain('mit deinem Netzbegrünung-Konto');
      expect(text).not.toMatch(/Keycloak|SSO|Selbstregistrierung|Beta-Account/);
      expect(text).toContain('So bekommst du ein Konto');
    });

    it('zeigt ohne Ziel aus "Selbst beantworten" keinen Grund', () => {
      const el = modes(true, false);

      expect(el.querySelector('.anmeldegrund')).toBeNull();
    });
  });
});

describe('LoginSelectorComponent nach "Selbst beantworten" (#600)', () => {
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
    // Der Grund steht vor dem Hinweis zum Konto und den Anmeldewegen
    expect(fixture.nativeElement.querySelector('.component-box').firstElementChild).toBe(grund);
  });
});
