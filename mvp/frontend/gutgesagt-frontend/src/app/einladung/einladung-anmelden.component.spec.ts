import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { Router, provideRouter } from '@angular/router';
import { EinladungAnmeldenComponent } from './einladung-anmelden.component';
import { environment } from '../../environments/environment';

describe('EinladungAnmeldenComponent', () => {
  let fixture: ComponentFixture<EinladungAnmeldenComponent>;
  let http: HttpTestingController;
  let router: Router;
  let fenster: { location: { href: string } };

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [EinladungAnmeldenComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideNoopAnimations(), provideRouter([])],
    });
    fixture = TestBed.createComponent(EinladungAnmeldenComponent);
    http = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
    spyOn(router, 'navigateByUrl').and.resolveTo(true);
    spyOn(router, 'navigate').and.resolveTo(true);
    fenster = { location: { href: '' } };
    fixture.componentInstance.fenster = fenster as unknown as Pick<Window, 'location'>;
    fixture.detectChanges();
  });

  afterEach(() => {
    http.verify();
    sessionStorage.clear();
  });

  function abgemeldet() {
    http.expectOne(`${environment.baseUrl}/api/check-session`).flush('nein', { status: 401, statusText: 'Unauthorized' });
  }

  it('startet ohne Sitzung gleich die Keycloak-Anmeldung, zurueck auf die Startseite', () => {
    abgemeldet();
    http.expectOne(`${environment.baseUrl}/api/auth/modes`).flush({ keycloakEnabled: true, managedAuthEnabled: false });

    expect(fenster.location.href).toBe(`${environment.baseUrl}/api/auth/login/keycloak?returnUrl=%2F`);
    // Keine Mail-Adresse in der Adresse (Zugriffsprotokolle)
    expect(fenster.location.href).not.toContain('login_hint');
  });

  it('nimmt im Zweifel die Keycloak-Anmeldung, wenn /api/auth/modes scheitert', () => {
    abgemeldet();
    http.expectOne(`${environment.baseUrl}/api/auth/modes`).flush('kaputt', { status: 500, statusText: 'Fehler' });

    expect(fenster.location.href).toContain('/api/auth/login/keycloak');
  });

  it('fuehrt ohne Keycloak (Entwicklung) zur Login-Auswahl', () => {
    abgemeldet();
    http.expectOne(`${environment.baseUrl}/api/auth/modes`).flush({ keycloakEnabled: false, managedAuthEnabled: true });

    expect(router.navigate).toHaveBeenCalledWith(['/login']);
    expect(fenster.location.href).toBe('');
  });

  it('schickt Angemeldete auf die Startseite, ohne neue Anmeldung', () => {
    http.expectOne(`${environment.baseUrl}/api/check-session`).flush({ ok: true });

    expect(router.navigateByUrl).toHaveBeenCalledWith('/');
    expect(fenster.location.href).toBe('');
  });

  it('hat einen Knopf, falls die Weiterleitung nicht losgeht', () => {
    abgemeldet();
    http.expectOne(`${environment.baseUrl}/api/auth/modes`).flush({ keycloakEnabled: true, managedAuthEnabled: false });
    fenster.location.href = '';
    fixture.detectChanges();

    const knopf = (fixture.nativeElement as HTMLElement).querySelector('button')!;
    expect(knopf.textContent).toContain('Jetzt anmelden');
    knopf.click();
    expect(fenster.location.href).toContain('/api/auth/login/keycloak');
  });
});
