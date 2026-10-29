import { ComponentFixture, TestBed } from '@angular/core/testing';
import { LoginComponent } from './login.component';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { Router, ActivatedRoute } from '@angular/router';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { of } from 'rxjs';
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
