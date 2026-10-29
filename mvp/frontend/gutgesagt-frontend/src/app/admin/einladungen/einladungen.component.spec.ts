import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { EinladungenComponent } from './einladungen.component';
import { Einladung } from '../../shared/einladung/einladung.service';
import { environment } from '../../../environments/environment';

const URL = `${environment.baseUrl}/api/v1/einladungen`;

const GRUPPE: Einladung = {
  id: 'e1',
  code: 'GruppenCode123',
  notiz: 'Kreisverband, Herbsttreffen',
  erlaubte_konten: 50,
  angelegte_konten: 3,
  gueltig_bis: '2026-11-27',
  abgeschaltet: false,
  angelegt_am: '2026-10-30',
  zustand: 'aktiv',
};

describe('EinladungenComponent', () => {
  let fixture: ComponentFixture<EinladungenComponent>;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EinladungenComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideNoopAnimations()],
    }).compileComponents();

    fixture = TestBed.createComponent(EinladungenComponent);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  });

  afterEach(() => http.verify());

  function el(): HTMLElement {
    return fixture.nativeElement as HTMLElement;
  }

  function laden(einladungen: Einladung[], eingerichtet = true) {
    http.expectOne(URL).flush({ registrierung_eingerichtet: eingerichtet, einladungen });
    fixture.detectChanges();
  }

  it('zeigt Notiz, Zaehler, letzten Tag, Zustand und Link', () => {
    laden([GRUPPE]);

    const zeile = el().querySelector('[data-testid="einladung"]')!;
    expect(zeile.textContent).toContain('Kreisverband, Herbsttreffen');
    expect(zeile.textContent).toContain('3 von 50');
    expect(zeile.textContent).toContain('27.11.2026');
    expect(zeile.textContent).toContain('aktiv');
    expect(zeile.textContent).toContain(`${window.location.origin}/einladung#GruppenCode123`);
  });

  it('legt eine Einladung mit Notiz, Zahl und letztem Tag an', () => {
    laden([]);
    const komponente = fixture.componentInstance;
    komponente.notiz = 'Persönlicher Link';
    komponente.erlaubteKonten = 1;
    komponente.gueltigBis = '2026-11-13';

    komponente.anlegen();

    const anfrage = http.expectOne((r) => r.method === 'POST' && r.url === URL);
    expect(anfrage.request.body).toEqual({
      notiz: 'Persönlicher Link',
      erlaubte_konten: 1,
      gueltig_bis: '2026-11-13',
    });
    anfrage.flush({ ...GRUPPE, id: 'e2', notiz: 'Persönlicher Link', erlaubte_konten: 1, angelegte_konten: 0 });
    fixture.detectChanges();

    expect(el().querySelectorAll('[data-testid="einladung"]').length).toBe(1);
    expect(el().textContent).toContain('0 von 1');
  });

  it('schaltet eine Einladung ab', () => {
    laden([GRUPPE]);

    (el().querySelector('[data-testid="schalten"]') as HTMLButtonElement).click();

    const anfrage = http.expectOne(`${URL}/e1`);
    expect(anfrage.request.method).toBe('PATCH');
    expect(anfrage.request.body).toEqual({ abgeschaltet: true });
    anfrage.flush({ ...GRUPPE, abgeschaltet: true, zustand: 'abgeschaltet' });
    fixture.detectChanges();

    expect(el().querySelector('[data-testid="einladung"]')!.textContent).toContain('abgeschaltet');
    expect(el().querySelector('[data-testid="schalten"]')!.textContent).toContain('Einschalten');
  });

  it('warnt, wenn Einloesen nicht eingerichtet ist', () => {
    laden([GRUPPE], false);

    expect(el().textContent).toContain('noch nicht eingerichtet');
  });

  it('meldet einen Ladefehler', () => {
    http.expectOne(URL).flush('kaputt', { status: 500, statusText: 'Server Error' });
    fixture.detectChanges();

    expect(el().textContent).toContain('konnten nicht geladen werden');
  });
});
