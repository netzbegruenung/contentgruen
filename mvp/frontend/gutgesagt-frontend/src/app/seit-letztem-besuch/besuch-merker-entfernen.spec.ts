import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Subject } from 'rxjs';

import { environment } from '../../environments/environment';
import { AuthService } from '../auth/auth.service';
import { Art9EinwilligungService } from '../services/art9-einwilligung.service';
import { besuchMerkerSchreiben, besuchSchluessel } from './besuch-merker';

/** Der Merker „Seit deinem letzten Besuch“ gehoert zum Konto (Nutzerfuehrung 13.11.). */
describe('Merker „Seit deinem letzten Besuch“ beim Abmelden und Widerruf', () => {
  let http: HttpTestingController;
  let auth: AuthService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: Router,
          useValue: { url: '/', navigate: jasmine.createSpy('navigate'), events: new Subject<unknown>(), getCurrentNavigation: () => null },
        },
      ],
    });
    http = TestBed.inject(HttpTestingController);
    auth = TestBed.inject(AuthService);
    auth.setUserInfo({ isAuthenticated: true, userId: 'kim-1', userName: 'Kim', claims: null });
    besuchMerkerSchreiben('kim-1', { zeit: '2026-11-11T00:00:00Z', aussagen: ['a'] });
    besuchMerkerSchreiben('kim-2', { zeit: '2026-11-11T00:00:00Z', aussagen: [] });
  });

  afterEach(() => {
    localStorage.removeItem(besuchSchluessel('kim-1'));
    localStorage.removeItem(besuchSchluessel('kim-2'));
  });

  it('entfernt beim Abmelden nur den Merker des Kontos', () => {
    // Der Merker geht schon vor der Antwort; die Fehlerantwort vermeidet das Neuladen der Seite.
    auth.logout();
    expect(localStorage.getItem(besuchSchluessel('kim-1'))).toBeNull();
    spyOn(console, 'error');
    http.expectOne(`${environment.baseUrl}/api/auth/logout`).flush(null, { status: 500, statusText: 'Server Error' });

    expect(localStorage.getItem(besuchSchluessel('kim-1'))).toBeNull();
    expect(localStorage.getItem(besuchSchluessel('kim-2'))).not.toBeNull();
  });

  it('entfernt beim Widerruf der Art.-9-Einwilligung den Merker des Kontos', () => {
    TestBed.inject(Art9EinwilligungService).widerrufen().subscribe();
    http.expectOne({ method: 'DELETE', url: `${environment.baseUrl}/api/v1/art9-einwilligung` }).flush(null);

    expect(localStorage.getItem(besuchSchluessel('kim-1'))).toBeNull();
    expect(localStorage.getItem(besuchSchluessel('kim-2'))).not.toBeNull();
  });
});
