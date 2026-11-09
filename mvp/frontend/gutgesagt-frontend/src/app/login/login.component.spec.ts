import { ComponentFixture, TestBed } from '@angular/core/testing';
import { LoginComponent } from './login.component';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { Router, ActivatedRoute } from '@angular/router';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { of, throwError } from 'rxjs';
import { MatSnackBar } from '@angular/material/snack-bar';
import { AuthService } from '../auth/auth.service';
import { ORGANISATION } from '../shared/organisation';
import { RUECKKEHRZIEL_SCHLUESSEL } from './rueckkehrziel';

describe('LoginComponent', () => {
  let component: LoginComponent;
  let fixture: ComponentFixture<LoginComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        LoginComponent,
        HttpClientTestingModule,
        BrowserAnimationsModule
      ],
      providers: [
        { provide: Router, useValue: {
          navigate: jasmine.createSpy('navigate'),
          navigateByUrl: jasmine.createSpy('navigateByUrl'),
          url: '/login' // Add url property for the component constructor
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

    fixture = TestBed.createComponent(LoginComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('fragt immer nach E-Mail-Adresse und Passwort, nie nach einem Benutzernamen (#488)', () => {
    const el: HTMLElement = fixture.nativeElement;

    expect(el.querySelector('input[formControlName="email"]')).not.toBeNull();
    expect(el.querySelector('input[formControlName="username"]')).toBeNull();
  });

  describe('falsche Zugangsdaten und Passwort vergessen (#645)', () => {
    function anmeldenMitFehler(): HTMLElement {
      spyOn(TestBed.inject(AuthService), 'loginWithManagedAuth').and.returnValue(
        throwError(() => new Error('401')),
      );
      component.loginForm.setValue({ email: 'jemand@example.org', password: 'falsch123' });
      component.onLogin();
      fixture.detectChanges();
      return fixture.nativeElement as HTMLElement;
    }

    it('meldet sie genau einmal, am Passwortfeld, mit role=alert und ohne Snackbar', () => {
      const snackbar = spyOn(TestBed.inject(MatSnackBar), 'open');
      const el = anmeldenMitFehler();

      const meldungen = el.querySelectorAll('[role="alert"]');
      expect(meldungen.length).toBe(1);
      expect(meldungen[0].textContent!.trim()).toBe('E-Mail-Adresse oder Passwort stimmt nicht.');
      expect(meldungen[0].classList).toContain('anmeldefehler');
      expect(snackbar).not.toHaveBeenCalled();

      const passwort = el.querySelector('input[formControlName="password"]')!;
      expect(passwort.getAttribute('aria-invalid')).toBe('true');
      expect(passwort.getAttribute('aria-describedby')).toContain('anmeldefehler');
      // Die Meldung steht direkt unter dem Passwortfeld, vor dem Knopf.
      expect(passwort.closest('mat-form-field')!.nextElementSibling).toBe(meldungen[0]);
    });

    it('nimmt die Meldung beim nächsten Versuch zurück', () => {
      anmeldenMitFehler();
      (TestBed.inject(AuthService).loginWithManagedAuth as jasmine.Spy).and.returnValue(of({} as any));
      component.onLogin();
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelector('[role="alert"]')).toBeNull();
    });

    it('nennt bei "Passwort vergessen?" dieselbe Mail wie "So bekommst du ein Konto"', () => {
      const hinweis = (fixture.nativeElement as HTMLElement).querySelector('.passwort-vergessen')!;
      const link = hinweis.querySelector('a')!;

      expect(hinweis.textContent).toContain('Passwort vergessen?');
      expect(link.textContent!.trim()).toBe(ORGANISATION.gutgesagtMail);
      expect(link.getAttribute('href')).toMatch(new RegExp(`^mailto:${ORGANISATION.gutgesagtMail}\\?subject=`));
    });
  });

  describe('Rueckkehrziel (Befund 10 aus dem Review zu PR 458)', () => {
    function mitParametern(queryParams: Record<string, string>): LoginComponent {
      TestBed.inject(ActivatedRoute).snapshot.queryParams = queryParams;
      return TestBed.createComponent(LoginComponent).componentInstance;
    }

    beforeEach(() => sessionStorage.removeItem(RUECKKEHRZIEL_SCHLUESSEL));
    afterEach(() => sessionStorage.removeItem(RUECKKEHRZIEL_SCHLUESSEL));

    it('legt ohne Rueckkehrziel kein "/" ab, auch nicht bei einer Login-Seite als Ziel', () => {
      const login = mitParametern({ returnUrl: '/login/managed' });

      expect(login.returnUrl).toBe('/');
      expect(sessionStorage.getItem(RUECKKEHRZIEL_SCHLUESSEL)).toBeNull();
    });

    it('merkt sich ein echtes Ziel und findet es ohne Parameter wieder', () => {
      mitParametern({ returnUrl: '/contribute' });

      expect(sessionStorage.getItem(RUECKKEHRZIEL_SCHLUESSEL)).toBe('/contribute');
      expect(mitParametern({}).returnUrl).toBe('/contribute');
    });

    it('startet auch, wenn der Browser den sessionStorage sperrt', () => {
      const spione = [
        spyOn(Storage.prototype, 'getItem').and.throwError('SecurityError'),
        spyOn(Storage.prototype, 'setItem').and.throwError('SecurityError'),
      ];

      expect(mitParametern({}).returnUrl).toBe('/');
      expect(mitParametern({ returnUrl: '/contribute' }).returnUrl).toBe('/contribute');
      spione.forEach((spion) => spion.and.callThrough());
    });
  });
});
