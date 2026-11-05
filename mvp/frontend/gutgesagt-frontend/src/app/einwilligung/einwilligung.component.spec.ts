import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { EinwilligungComponent } from './einwilligung.component';
import { Art9EinwilligungStand } from '../services/art9-einwilligung.service';
import { environment } from '../../environments/environment';

const URL = `${environment.baseUrl}/api/v1/art9-einwilligung`;
const WORTLAUT = { kennung: '2026-11-05', text: 'Ich willige ausdrücklich ein, dass …' };

function stand(teil: Partial<Art9EinwilligungStand> = {}): Art9EinwilligungStand {
  return {
    eingewilligt: false,
    wortlaut: null,
    eingewilligt_am: null,
    widerrufen_am: null,
    aktueller_wortlaut: WORTLAUT,
    ...teil,
  };
}

/** Die Art.-9-Einwilligung (#489): eigenes Haekchen, nichts vorbelegt, widerrufbar. */
describe('EinwilligungComponent', () => {
  let fixture: ComponentFixture<EinwilligungComponent>;
  let http: HttpTestingController;
  let router: Router;

  function starten(returnUrl: string | null = '/einwerfen') {
    TestBed.configureTestingModule({
      imports: [EinwilligungComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideNoopAnimations(),
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { queryParamMap: convertToParamMap(returnUrl ? { returnUrl } : {}) } },
        },
      ],
    });
    fixture = TestBed.createComponent(EinwilligungComponent);
    http = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
    spyOn(router, 'navigateByUrl').and.resolveTo(true);
    fixture.detectChanges();
  }

  function standLiefern(s: Art9EinwilligungStand) {
    http.expectOne({ method: 'GET', url: URL }).flush(s);
    fixture.detectChanges();
  }

  function el(): HTMLElement {
    return fixture.nativeElement as HTMLElement;
  }

  function knopf(text: string): HTMLButtonElement {
    const treffer = Array.from(el().querySelectorAll('button')).find((b) => b.textContent?.includes(text));
    if (!treffer) {
      throw new Error(`Kein Knopf "${text}"`);
    }
    return treffer as HTMLButtonElement;
  }

  afterEach(() => http.verify());

  describe('Frage', () => {
    it('zeigt den Wortlaut vom Backend am Haekchen, nicht angehakt', () => {
      starten();
      standLiefern(stand());

      const haekchen = el().querySelector('mat-checkbox input[type=checkbox]') as HTMLInputElement;
      expect(el().querySelector('mat-checkbox')?.textContent).toContain(WORTLAUT.text);
      expect(haekchen.checked).toBeFalse();
      expect(knopf('Einwilligen und weiter').disabled).toBeTrue();
    });

    it('ohne Haekchen geht nichts ans Backend', () => {
      starten();
      standLiefern(stand());

      fixture.componentInstance.einwilligen();

      http.expectNone({ method: 'POST', url: URL });
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });

    it('mit Haekchen schickt die Kennung des gezeigten Wortlauts und fuehrt zurueck', () => {
      starten('/einwerfen?von=fangkorb');
      standLiefern(stand());

      fixture.componentInstance.angehakt = true;
      fixture.detectChanges();
      knopf('Einwilligen und weiter').click();

      const anfrage = http.expectOne({ method: 'POST', url: URL });
      expect(anfrage.request.body).toEqual({ wortlaut: '2026-11-05' });
      anfrage.flush(null, { status: 204, statusText: 'No Content' });
      expect(router.navigateByUrl).toHaveBeenCalledWith('/einwerfen?von=fangkorb');
    });

    it('ohne Einwilligung weiter speichert nichts', () => {
      starten('/einwerfen');
      standLiefern(stand());

      knopf('Ohne Einwilligung weiter').click();

      http.expectNone({ method: 'POST', url: URL });
      expect(router.navigateByUrl).toHaveBeenCalledWith('/einwerfen');
    });

    it('fuehrt nur innerhalb der App zurueck', () => {
      starten('//fremd.example/');
      standLiefern(stand());

      knopf('Ohne Einwilligung weiter').click();

      expect(router.navigateByUrl).toHaveBeenCalledWith('/search');
    });
  });

  describe('Stand und Widerruf', () => {
    it('zeigt Zeitpunkt und Wortlaut der Einwilligung', () => {
      starten(null);
      standLiefern(stand({ eingewilligt: true, wortlaut: '2026-11-05', eingewilligt_am: '2026-11-05T09:30:00Z' }));

      expect(el().textContent).toContain('05.11.2026');
      expect(el().querySelector('.wortlaut')?.textContent).toContain(WORTLAUT.text);
      expect(el().querySelector('mat-checkbox')).toBeNull();
    });

    it('widerrufen fragt danach erneut, ohne Haekchen', () => {
      starten(null);
      standLiefern(stand({ eingewilligt: true, wortlaut: '2026-11-05', eingewilligt_am: '2026-11-05T09:30:00Z' }));

      knopf('Einwilligung widerrufen').click();
      http.expectOne({ method: 'DELETE', url: URL }).flush(null, { status: 204, statusText: 'No Content' });
      standLiefern(stand({ wortlaut: '2026-11-05', widerrufen_am: '2026-11-06T09:30:00Z' }));

      expect(el().textContent).toContain('widerrufen');
      expect(fixture.componentInstance.angehakt).toBeFalse();
      expect(knopf('Einwilligen und weiter').disabled).toBeTrue();
    });
  });

  it('zeigt einen Fehler, wenn der Stand nicht kommt', () => {
    starten();
    http.expectOne({ method: 'GET', url: URL }).flush(null, { status: 500, statusText: 'Fehler' });
    fixture.detectChanges();

    expect(el().querySelector('[role=alert]')).not.toBeNull();
  });
});
