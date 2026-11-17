import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { BehaviorSubject } from 'rxjs';
import { ANMELDEN_KNOPF, ANMELDEN_KNOPF_OHNE_KEYCLOAK, MitKontoComponent, VORSCHAU_ETIKETT, VORSCHAU_SATZ, WEITER_SUCHEN } from './mit-konto.component';
import { VORSCHAU_SCHRITTE } from './vorschau-schritte';
import { RUECKKEHRZIEL_SCHLUESSEL } from '../login/rueckkehrziel';

describe('MitKontoComponent', () => {
  let fixture: ComponentFixture<MitKontoComponent>;
  let http: HttpTestingController;
  let query: BehaviorSubject<ReturnType<typeof convertToParamMap>>;
  let fenster: { location: { href: string } };

  function starten(params: Record<string, string>, modes = { keycloakEnabled: true, managedAuthEnabled: false }): HTMLElement {
    query = new BehaviorSubject(convertToParamMap(params));
    TestBed.configureTestingModule({
      imports: [MitKontoComponent],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ActivatedRoute, useValue: { queryParamMap: query, snapshot: { queryParamMap: query.value } } },
      ],
    });
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(MitKontoComponent);
    fenster = { location: { href: '' } };
    fixture.componentInstance.fenster = fenster as unknown as Window;
    fixture.detectChanges();
    http.expectOne((r) => r.url.endsWith('/api/auth/modes')).flush(modes);
    fixture.detectChanges();
    return fixture.nativeElement;
  }

  const text = (el: Element | null) => (el?.textContent ?? '').replace(/\s+/g, ' ').trim();

  afterEach(() => {
    http.verify();
    sessionStorage.removeItem(RUECKKEHRZIEL_SCHLUESSEL);
  });

  describe('Übersicht', () => {
    it('zeigt Überschrift und alle drei Schritte mit Bild, Satz und Alternativtext', () => {
      const seite = starten({ ziel: '/einwerfen' });
      expect(text(seite.querySelector('.mk-titel'))).toBe('Das erwartet dich mit Konto');
      const schritte = seite.querySelectorAll('.mk-schritt');
      expect(schritte.length).toBe(3);
      VORSCHAU_SCHRITTE.forEach((s, i) => {
        expect(text(schritte[i].querySelector('.mk-schritt-titel'))).toBe(s.titel);
        expect(text(schritte[i].querySelector('.mk-schritt-satz'))).toBe(s.satz);
        const bild = schritte[i].querySelector('img') as HTMLImageElement;
        expect(bild.getAttribute('src')).toBe(s.bild);
        expect(bild.alt).toBe(`Vorschau: ${s.alt}`);
      });
    });

    it('zeigt sich als Tour: Wegweiser, Vorschau-Satz und jedes Bild im Rahmen mit Etikett', () => {
      const seite = starten({ ziel: '/einwerfen' });
      expect(seite.querySelector('.mk-band .mk-wegweiser')).not.toBeNull();
      expect(text(seite.querySelector('.mk-vorschau-satz'))).toBe(VORSCHAU_SATZ);
      const rahmen = seite.querySelectorAll('.mk-rahmen');
      expect(rahmen.length).toBe(3);
      rahmen.forEach((r) => {
        expect(text(r.querySelector('.mk-etikett'))).toBe(VORSCHAU_ETIKETT);
        const bild = r.querySelector('img') as HTMLImageElement;
        expect(bild.closest('a, button')).toBeNull();
        expect(bild.getAttribute('draggable')).toBe('false');
      });
    });

    it('meldet mit dem Netzbegrünung-Konto an und merkt sich das Ziel', () => {
      const seite = starten({ ziel: '/einwerfen?von=fangkorb' });
      const knopf = seite.querySelector('.mk-anmelden') as HTMLButtonElement;
      expect(text(knopf)).toContain(ANMELDEN_KNOPF);
      knopf.click();
      expect(fenster.location.href).toContain('/api/auth/login/keycloak?returnUrl=%2Feinwerfen%3Fvon%3Dfangkorb');
      expect(sessionStorage.getItem(RUECKKEHRZIEL_SCHLUESSEL)).toBe('/einwerfen?von=fangkorb');
    });

    it('führt ohne Netzbegrünung-Anmeldung zur Login-Auswahl, mit Ziel', () => {
      const seite = starten({ ziel: '/fangkorb' }, { keycloakEnabled: false, managedAuthEnabled: true });
      const navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
      const knopf = seite.querySelector('.mk-anmelden') as HTMLButtonElement;
      expect(text(knopf)).toContain(ANMELDEN_KNOPF_OHNE_KEYCLOAK);
      knopf.click();
      expect(navigate).toHaveBeenCalledWith(['/login'], { queryParams: { returnUrl: '/fangkorb' } });
      expect(fenster.location.href).toBe('');
    });

    it('bietet den Weg zurück zur Suche und zu „Noch kein Konto?“ auf der Anmeldung', () => {
      const seite = starten({ ziel: '/contribute' });
      const zurueck = seite.querySelector('.mk-weiter-suchen') as HTMLAnchorElement;
      expect(text(zurueck)).toBe(WEITER_SUCHEN);
      expect(zurueck.getAttribute('href')).toBe('/search');
      const kontoWeg = seite.querySelector('.mk-konto-weg a') as HTMLAnchorElement;
      expect(kontoWeg.getAttribute('href')).toBe('/login?returnUrl=%2Fcontribute#noch-kein-konto');
    });

    it('nimmt ein fremdes Ziel nicht an', () => {
      const seite = starten({ ziel: '//fremd.example' });
      (seite.querySelector('.mk-anmelden') as HTMLButtonElement).click();
      expect(fenster.location.href).toContain('returnUrl=%2Fcontribute');
    });
  });

  describe('Rundgang ohne Konto', () => {
    it('zeigt dieselben Schritte einzeln und die Anmeldung erst am Ende', () => {
      const seite = starten({ ansicht: 'rundgang', ziel: '/contribute' });
      expect(seite.querySelectorAll('.mk-schritt').length).toBe(0);
      VORSCHAU_SCHRITTE.forEach((s, i) => {
        expect(text(seite.querySelector('.mk-geschichte .mk-schritt-titel'))).toBe(`Schritt ${i + 1} von 3: ${s.titel}`);
        expect(text(seite.querySelector('.mk-geschichte .mk-schritt-satz'))).toBe(s.satz);
        expect((seite.querySelector('.mk-geschichte img') as HTMLImageElement).alt).toBe(`Vorschau: ${s.alt}`);
        expect(text(seite.querySelector('.mk-zaehler'))).toBe(`Schritt ${i + 1} von 3`);
        const punkte = Array.from(seite.querySelectorAll('.mk-punkt'));
        expect(punkte.map((p) => p.classList.contains('aktiv'))).toEqual([0, 1, 2].map((j) => j === i));
        expect(!!seite.querySelector('.mk-zurueck')).toBe(i > 0);
        const weiter = seite.querySelector('.mk-weiter') as HTMLButtonElement | null;
        if (i < 2) {
          expect(seite.querySelector('.mk-anmelden')).toBeNull();
          weiter!.click();
          fixture.detectChanges();
        } else {
          expect(weiter).toBeNull();
          expect(text(seite.querySelector('.mk-anmelden'))).toContain(ANMELDEN_KNOPF);
          expect(seite.querySelector('.mk-weiter-suchen')).not.toBeNull();
        }
      });
    });

    it('blättert zurück und setzt den Fokus auf den Titel des Bildes', async () => {
      const seite = starten({ ansicht: 'rundgang' });
      (seite.querySelector('.mk-weiter') as HTMLButtonElement).click();
      fixture.detectChanges();
      await Promise.resolve();
      expect(document.activeElement).toBe(seite.querySelector('.mk-geschichte .mk-schritt-titel'));
      (seite.querySelector('.mk-zurueck') as HTMLButtonElement).click();
      fixture.detectChanges();
      expect(text(seite.querySelector('.mk-geschichte .mk-schritt-titel'))).toContain(VORSCHAU_SCHRITTE[0].titel);
    });
  });
});
