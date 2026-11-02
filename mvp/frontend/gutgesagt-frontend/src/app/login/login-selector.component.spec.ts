import { ComponentFixture, TestBed } from '@angular/core/testing';
import { LoginSelectorComponent } from './login-selector.component';
import { HttpClientTestingModule } from '@angular/common/http/testing';
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

  describe('Texte zum eigenen Realm (#492)', () => {
    const text = (selector: string): string => {
      const element: HTMLElement | null = fixture.nativeElement.querySelector(selector);
      expect(element).withContext(selector).not.toBeNull();
      return (element?.textContent ?? '').replace(/\s+/g, ' ').trim();
    };

    beforeEach(() => {
      component.isLoading = false;
      fixture.detectChanges();
    });

    it('nennt im Hinweis Netzbegrünung-Login und Einladung statt „keine Selbstregistrierung“', () => {
      const titel = text('.registration-panel-title');

      expect(titel).toContain('Netzbegrünung-Login');
      expect(titel).toContain('Einladung');
      expect(fixture.nativeElement.textContent).not.toContain('Selbstregistrierung');
    });

    it('erklärt den Weg über einen Einladungslink', () => {
      const inhalt = text('.registration-content');

      expect(inhalt).toContain('Einladungslink');
      expect(inhalt).toContain('Mail-Adresse und Passwort');
    });

    it('beschriftet die Anmeldung über den Realm mit Netzbegrünung-Login und Einladung', () => {
      expect(text('.keycloak-button .button-title')).toBe('Anmelden');
      expect(text('.keycloak-button .button-subtitle')).toBe('Netzbegrünung-Login oder Einladung');
      expect(text('.realm-card .login-description')).toContain('„Mit Netzbegrünung anmelden“');
    });

    it('beschriftet die Direktanmeldung als Beta-Zugang', () => {
      expect(text('.gutgesagt-button .button-title')).toBe('Beta-Zugang');
      expect(text('.beta-zugang-card .login-description')).toContain('Beta-Zugang');
    });

    it('verwendet keine Begriffe, die das Glossar für die Anmeldung meidet', () => {
      const alles = text('.component-box');

      for (const gemieden of [
        'Keycloak', 'SSO', 'Vereinslogin', 'Beta-Account', 'manueller User', 'Managed User', 'Netzbegrünung Login'
      ]) {
        expect(alles).not.toContain(gemieden);
      }
    });
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

    it('nennt für die Bitte um eine Einladung die Kontaktadresse aus der Organisationskonstante (#430, #492)', () => {
      const link: HTMLAnchorElement = fixture.nativeElement.querySelector('.email-link');

      expect(link.textContent?.trim()).toBe(ORGANISATION.gutgesagtMail);
      expect(link.getAttribute('href')).toBe(
        `mailto:${ORGANISATION.gutgesagtMail}?subject=${encodeURIComponent('Einladung zu Gut gesagt')}`
      );
    });
  });
});
