import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { ActivatedRoute, provideRouter } from '@angular/router';
import { EinladungComponent } from './einladung.component';
import { environment } from '../../environments/environment';

const URL = `${environment.baseUrl}/api/v1/einladungen`;

describe('EinladungComponent', () => {
  let fixture: ComponentFixture<EinladungComponent>;
  let http: HttpTestingController;

  function starten(fragment: string | null) {
    TestBed.configureTestingModule({
      imports: [EinladungComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideNoopAnimations(),
        provideRouter([]),
        { provide: ActivatedRoute, useValue: { snapshot: { fragment } } },
      ],
    });
    fixture = TestBed.createComponent(EinladungComponent);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  }

  afterEach(() => http.verify());

  function el(): HTMLElement {
    return fixture.nativeElement as HTMLElement;
  }

  function pruefen(einloesbar: boolean) {
    const anfrage = http.expectOne(`${URL}/pruefen`);
    expect(anfrage.request.body).toEqual({ code: 'Code123' });
    anfrage.flush({ einloesbar });
    fixture.detectChanges();
  }

  function absenden(email: string) {
    fixture.componentInstance.email = email;
    fixture.componentInstance.einloesen();
    return http.expectOne(`${URL}/einloesen`);
  }

  it('ohne Code im Link gibt es nichts einzuloesen', () => {
    starten(null);

    expect(el().textContent).toContain('gilt nicht');
  });

  it('eine ungueltige Einladung zeigt kein Formular', () => {
    starten('Code123');
    pruefen(false);

    expect(el().textContent).toContain('gilt nicht');
    expect(el().querySelector('input[type="email"]')).toBeNull();
  });

  it('legt mit der Mail-Adresse ein Konto an und verweist auf die Mail', () => {
    starten('Code123');
    pruefen(true);
    expect(el().querySelector('input[type="email"]')).not.toBeNull();

    const anfrage = absenden('neu@example.org');
    expect(anfrage.request.body).toEqual({ code: 'Code123', email: 'neu@example.org' });
    anfrage.flush({ success: true }, { status: 202, statusText: 'Accepted' });
    fixture.detectChanges();

    expect(el().textContent).toContain('Postfach');
    expect(el().textContent).toContain('Passwort vergessen');
  });

  it('meldet, wenn die Einladung inzwischen nicht mehr gilt', () => {
    starten('Code123');
    pruefen(true);

    absenden('neu@example.org').flush('weg', { status: 410, statusText: 'Gone' });
    fixture.detectChanges();

    expect(el().textContent).toContain('gilt nicht');
  });

  it('meldet einen Fehler beim Anlegen und laesst es erneut versuchen', () => {
    starten('Code123');
    pruefen(true);

    absenden('neu@example.org').flush('kaputt', { status: 502, statusText: 'Bad Gateway' });
    fixture.detectChanges();

    expect(el().textContent).toContain('hat nicht geklappt');
    expect(el().querySelector('input[type="email"]')).not.toBeNull();
  });
});
